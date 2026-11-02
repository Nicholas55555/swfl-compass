"""SWFL Compass agent — Gemini function-calling loop over SearXNG + scraper + RAG.

Flow per user turn:
  1. Tool loop: Gemini decides to `web_search` / `read_page` / `recall` (up to
     MAX_STEPS), each step streamed to the UI as a status event. Everything read is
     indexed in the chat's vector store (rag.py).
  2. Final answer (markdown) streamed as one event.
  3. Extras call (JSON mode): follow-up questions + the most helpful resources,
     chosen BY INDEX from sources actually seen — so URLs are never invented.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
import os
from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import types

import httpx

import maps
from rag import VectorStore, get_store
from scraper import FetchError, fetch_url
from searxng import searxng

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
# Tried in order when a model is overloaded (503) or rate-limited (429).
FALLBACKS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACKS", "gemini-3-flash-preview,gemini-3.5-flash-lite").split(",")
    if m.strip()
]
_last_good: str | None = None  # sticky: start with whatever answered last
_exhausted: set[str] = set()  # models whose free-tier DAILY quota is spent (per project)
MAX_STEPS = 3
DOC_MAX_STEPS = 6  # guides / itineraries research more
READ_FETCH_CHARS = 80_000  # whole page goes into the vector store...
READ_INTRO_CHARS = 1_500  # ...the model sees the intro plus the most relevant chunks
READ_TOP_K = 6

PERSONAS = {
    "resident": "a resident of Southwest Florida",
    "student": "a student (e.g. at FGCU, FSW, or Hodges) in Southwest Florida",
    "worker": "someone working (or looking for work) in Southwest Florida",
    "visitor": "a visitor/tourist to Southwest Florida",
}

SYSTEM = """You are SWFL Compass, a friendly, practical AI guide for people who live, study,
work in, or visit Southwest Florida (Lee, Collier, Charlotte, Hendry and Glades counties —
Fort Myers, Cape Coral, Naples, Bonita Springs, Estero, Sanibel, Punta Gorda, Immokalee, etc.).

Typical topics: hurricane prep & evacuation zones, flooding, red tide / water quality,
beaches & parks, local government services, transit (LeeTran, CAT), housing & utilities,
jobs & workforce programs, FGCU / FSW student life, healthcare, events, food assistance,
wildlife, permits, and tourism.

How you work:
- You are agentic: use `web_search` to find current, local, authoritative info (prefer .gov,
  county/city sites, FGCU, NOAA/NWS, FDEP, FWC, established local news). Use `read_page`
  when a snippet isn't enough or when the user asks you to summarize a resource.
- Keep searches few (usually 1-2) and SHORT (3-6 words, e.g. "LeeTran FGCU route").
  If a search returns 0 results, don't keep rephrasing — try at most one shorter query,
  then work with what you have (read the best page, or answer from general knowledge
  and say so).
- Answer concisely in markdown: short intro, bullets or steps, and inline markdown links
  to the sources you used. Be specific to SWFL — names, phone numbers, addresses when known.
- If something is time-sensitive (storms, closures), say to check the official source.
- If the question is vague, give your best useful answer and ask one clarifying question.
- Use `recall` first for follow-ups: it searches pages and results already gathered in
  this chat (a vector store), which is faster than searching the web again.
- For physical places (beaches, parks, restaurants, shelters, clinics, offices, attractions)
  call `find_places` — it returns verified Google Maps data (address, rating, open now, maps
  link). Link each place to its `maps_url`. The UI also shows these places on a map.
- Never invent URLs; only link URLs you got from tools.
"""

TASKS = {
    "itinerary": """Create a {days}-day itinerary for Southwest Florida.
Home base: {base}. Interests: {interests}. Notes: {notes}.
Research real, currently operating places: use `recall` first, `find_places` to pick and
verify places (one call per category, e.g. "beaches near Naples", "seafood restaurants Fort
Myers Beach"), and `web_search`/`read_page` for tips, hours or prices. Output ONE markdown document:
# <catchy title>
Short overview (who it's for, best season, getting around).
## Day 1 ... ## Day N, each with **Morning / Afternoon / Evening**: place name, 1-line why,
area/address, rating if known, rough cost ($/$$/$$$ or free), and its Google Maps link (maps_url).
## Where to eat (3-5 picks from find_places, with maps links)
## Practical tips (heat, sunscreen, hurricane season, red tide check, parking/tolls, traffic)
## Sources (links you used)""",
    "guide": """Create a practical guide document about: {topic}.
Use what we've discussed (call `recall` first) and research gaps with `web_search`.
Output ONE markdown document:
# <clear title>
A 2-3 sentence summary.
Sections with headings, numbered steps and checklists (- [ ] item) where useful.
## Key contacts & links (official names, phone numbers, websites; use find_places for locations)
## Sources (links you used)""",
}

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="web_search",
                description="Search the web (via SearXNG). Returns titles, URLs and snippets.",
                parameters={
                    "type": "OBJECT",
                    "properties": {"query": {"type": "STRING", "description": "Search query"}},
                    "required": ["query"],
                },
            ),
            types.FunctionDeclaration(
                name="read_page",
                description=(
                    "Fetch a web page or PDF by URL. The whole page is indexed; you get its intro "
                    "plus the passages most relevant to the user's question."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {"url": {"type": "STRING", "description": "Absolute URL"}},
                    "required": ["url"],
                },
            ),
            types.FunctionDeclaration(
                name="find_places",
                description=(
                    "Google Maps place search in Southwest Florida. Returns real places with "
                    "address, rating, review count, price level, open-now, website and maps_url."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "What and where, e.g. 'manatee viewing Fort Myers', 'hurricane shelters Cape Coral'",
                        }
                    },
                    "required": ["query"],
                },
            ),
            types.FunctionDeclaration(
                name="recall",
                description=(
                    "Semantic search over everything already gathered in this chat (pages read, "
                    "search results). Use before searching the web again."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {"query": {"type": "STRING", "description": "What to look for"}},
                    "required": ["query"],
                },
            ),
        ]
    )
]

EXTRAS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "suggested_questions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "resources": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "index": {"type": "INTEGER"},
                    "why": {"type": "STRING"},
                },
                "required": ["index", "why"],
            },
        },
    },
    "required": ["suggested_questions", "resources"],
}

_clients: list[genai.Client] = []
_next_key = 0  # round-robin cursor: spreads free-tier per-key quota across keys


def _keys() -> list[str]:
    keys = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
    single = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if single and single not in keys:
        keys.insert(0, single)
    return keys


def clients() -> list[genai.Client]:
    if not _clients:
        keys = _keys()
        if not keys:
            raise RuntimeError("GEMINI_API_KEY is not set (put it in backend/.env)")
        # SDK-level retries on 503 take ~45s each; we rotate keys/models instead.
        opts = types.HttpOptions(timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1))
        _clients.extend(genai.Client(api_key=k, http_options=opts) for k in keys)
    return _clients


async def generate(contents, config, model: str | None = None):
    """generate_content with key rotation + model fallback. Returns (response, model_used).

    429 (quota) → next key, same model. 503/500 (model overloaded) → next model.
    Pass `model` to pin one (a tool loop keeps its model so thought signatures stay valid);
    a pinned model still rotates keys and retries a 503 once.
    """
    global _last_good, _next_key
    from google.genai import errors

    pool = clients()
    order = [model] if model else list(dict.fromkeys([_last_good or MODEL, MODEL, *FALLBACKS]))
    last_err: Exception | None = None
    for m in order:
        if m in _exhausted and not model:
            continue
        overloaded = 0
        for _ in range(len(pool)):
            c = pool[_next_key % len(pool)]
            _next_key += 1
            try:
                resp = await c.aio.models.generate_content(model=m, contents=contents, config=config)
                _last_good = m
                return resp, m
            except errors.APIError as e:
                last_err = e
                if e.code == 429:
                    if "PerDay" in str(e):
                        _exhausted.add(m)  # daily cap — keys share a project, skip model
                        break
                    continue  # per-minute cap on this key — try the next key
                if e.code in (401, 403) and len(pool) > 1:
                    continue  # this key is rejected — try the next key
                if e.code not in (500, 503, 504):
                    raise
                overloaded += 1
                if model and overloaded == 1:
                    await asyncio.sleep(1.5)  # pinned: retry once before giving up
                    continue
                break  # model overloaded for everyone — next model
    raise last_err or RuntimeError("no model available")


async def _step(contents, config, model: str | None = None):
    """generate() that retries when Gemini returns neither text nor a function call
    (it intermittently finishes with MALFORMED_FUNCTION_CALL)."""
    for _ in range(3):
        resp, model = await generate(contents, config, model)
        if resp.function_calls or (resp.text or "").strip():
            break
    return resp, model


def _no_tools(config: types.GenerateContentConfig) -> types.GenerateContentConfig:
    """Same config, but the model must answer in text (tools stay declared so history is valid)."""
    return config.model_copy(update={"tool_config": types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(mode="NONE")
    )})


def _event(kind: str, **data: Any) -> str:
    return f"data: {json.dumps({'type': kind, **data})}\n\n"


def _history_to_contents(messages: list[dict]) -> list[types.Content]:
    out = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        out.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    return out


def _task_prompt(task: dict) -> str:
    if task.get("kind") == "itinerary":
        return TASKS["itinerary"].format(
            days=task.get("days") or 2,
            base=task.get("base") or "Fort Myers",
            interests=", ".join(task.get("interests") or []) or "a bit of everything",
            notes=task.get("notes") or "none",
        )
    return TASKS["guide"].format(topic=task.get("topic") or "what we've discussed in this chat")


async def run_agent(
    messages: list[dict],
    persona: str | None,
    session_id: str | None = None,
    task: dict | None = None,
) -> AsyncIterator[str]:
    store = get_store(session_id)
    question = messages[-1]["content"] if messages else ""
    if task:
        # Document mode: the visible user bubble is a short label; the real brief goes here.
        messages = [*messages[:-1], {"role": "user", "content": f"{question}\n\n{_task_prompt(task)}"}]
    max_steps = DOC_MAX_STEPS if task else MAX_STEPS

    sources: list[dict] = []  # every search result / page seen, in order
    places: dict[str, dict] = {}  # verified Google Maps places found this turn, by id
    seen_urls: set[str] = set()

    def remember(url: str, title: str, snippet: str = "") -> None:
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({"url": url, "title": title or url, "snippet": snippet})

    system = SYSTEM + f"\nToday's date is {date.today():%B %d, %Y}. Don't put years in search queries unless asked."
    if persona in PERSONAS:
        system += f"\nThe user is {PERSONAS[persona]}; tailor advice to them."

    contents = _history_to_contents(messages)
    config = types.GenerateContentConfig(
        system_instruction=system,
        tools=TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.4,
    )

    yield _event("status", text="🤔 Thinking…")
    if len(store):
        # Retrieval-augmented: ground this turn in what the chat already gathered.
        try:
            hits = [h for h in await store.search(question, k=5) if h["score"] > 0.55]
        except Exception as e:
            print(f"pre-retrieval failed: {e}")
            hits = []
        if hits:
            for h in hits:
                remember(h["url"], h["title"], h["text"][:200])
            notes_txt = "\n\n".join(f"[{h['title']}]({h['url']})\n{h['text']}" for h in hits)
            config = config.model_copy(update={"system_instruction": system + (
                "\n\nRelevant passages from earlier research in this chat (cite these links; "
                "search the web only if they don't cover the question):\n\n" + notes_txt
            )})
            yield _event("status", text=f"🧠 Found {len(hits)} relevant passages from earlier research")
    answer = ""
    model: str | None = None
    notes: list[str] = []  # plain-text record of tool results, for the fallback answer
    try:
        try:
            for step in range(max_steps + 1):
                if step == max_steps:
                    # Out of tool budget — force a final answer.
                    config = _no_tools(config)
                resp, model = await _step(contents, config, model)
                calls = resp.function_calls or []
                if not calls:
                    answer = resp.text or ""
                    break
                contents.append(resp.candidates[0].content)
                parts = []
                for call in calls:
                    args = dict(call.args or {})
                    result = await _run_tool(call.name, args, remember, store, question, places)
                    yield result.pop("_status")
                    notes.append(f"{call.name}({json.dumps(args)}) -> {json.dumps(result)[:6000]}")
                    parts.append(types.Part.from_function_response(name=call.name, response=result))
                contents.append(types.Content(role="user", parts=parts))
        except Exception as e:
            # Model overloaded mid-research: keep what we gathered and answer below.
            print(f"tool loop aborted: {type(e).__name__}: {e}")
            answer = ""

        if not answer.strip():
            # Gemini sometimes returns MALFORMED_FUNCTION_CALL / empty output. Answer from
            # the gathered research as plain text, with no tools in play at all.
            yield _event("status", text="✍️ Writing the answer…")
            convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
            prompt = (
                f"Conversation so far:\n{convo}\n\nResearch gathered:\n"
                + ("\n".join(notes) or "(none)")
                + "\n\nWrite the assistant's final answer to the last user message."
            )
            resp, _ = await _step(prompt, types.GenerateContentConfig(system_instruction=system))
            answer = resp.text or "Sorry — I couldn't put an answer together. Try rephrasing?"
    except Exception as e:  # surface API errors to the UI
        yield _event("error", text=f"{type(e).__name__}: {e}")
        yield _event("done")
        return

    yield _event("answer", text=answer, document=bool(task))
    if places:
        yield _event("places", places=_places_in_answer(places, answer))

    yield _event("status", text="Picking resources & next questions…")
    try:
        extras = await _extras(messages, answer, sources)
        yield _event("extras", **extras)
    except Exception as e:
        yield _event("extras", suggested_questions=[], resources=[], warning=str(e))
    yield _event("done")


_bg_tasks: set[asyncio.Task] = set()


def _background(coro) -> None:
    t = asyncio.create_task(coro)
    _bg_tasks.add(t)
    t.add_done_callback(_bg_tasks.discard)


async def _safe_index(coro) -> None:
    try:
        await coro
    except Exception as e:  # indexing is best-effort; the answer must not fail on it
        print(f"indexing failed: {type(e).__name__}: {e}")


async def _run_tool(
    name: str, args: dict, remember, store: VectorStore, question: str, places: dict[str, dict]
) -> dict:
    if name == "web_search":
        q = args.get("query", "")
        try:
            results = await searxng.search(q)
        except Exception as e:
            print(f"searxng failed: {e}")
            results = []
        via = ""
        if not results:
            results = await google_search(q)
            via = " (via Google)"
        for r in results:
            remember(r["url"], r["title"], r["snippet"])
        _background(_safe_index(store.add_snippets(results)))
        return {
            "results": results,
            "_status": _event("status", text=f"🔎 Searched “{q}” — {len(results)} results{via}"),
        }
    if name == "read_page":
        url = args.get("url", "")
        try:
            page = await fetch_url(url, max_chars=READ_FETCH_CHARS)
        except FetchError as e:
            page = await _read_via_gemini(url)  # site blocks scrapers; Gemini fetches it
            if page is None:
                return {"error": str(e), "_status": _event("status", text=f"Couldn't read {url}")}
        remember(page["url"], page["title"] or url)
        text = page["content"]
        if len(text) <= READ_INTRO_CHARS * 3:
            _background(_safe_index(store.add_page(page["url"], page["title"], text)))
            content = text
        else:
            try:
                await store.add_page(page["url"], page["title"], text)
                hits = await store.search(question, k=READ_TOP_K, url=page["url"])
                content = (
                    text[:READ_INTRO_CHARS]
                    + "\n\n...\n\nMost relevant passages:\n\n"
                    + "\n---\n".join(h["text"] for h in hits)
                )
            except Exception as e:
                print(f"RAG failed, truncating instead: {e}")
                content = text[:12_000]
        return {
            "title": page["title"],
            "content": content,
            "_status": _event("status", text=f"📄 Read {page['title'] or url}"),
        }
    if name == "find_places":
        q = args.get("query", "")
        if not maps.available():
            return {"error": "maps unavailable; use web_search", "_status": _event("status", text="Maps unavailable")}
        try:
            found = await maps.find_places(q)
        except Exception as e:
            return {"error": f"place search failed: {e}", "_status": _event("status", text=f"Place search failed: {q}")}
        for p in found:
            places.setdefault(p["id"], p)
        return {
            "places": found,
            "_status": _event("status", text=f"📍 Found {len(found)} places for “{q}” on Google Maps"),
        }
    if name == "recall":
        q = args.get("query", "")
        try:
            hits = await store.search(q, k=6)
        except Exception as e:
            return {"error": str(e), "_status": _event("status", text="Recall failed")}
        for h in hits:
            remember(h["url"], h["title"], h["text"][:200])
        return {
            "passages": [{"text": h["text"], "url": h["url"], "title": h["title"]} for h in hits],
            "_status": _event(
                "status", text=f"🧠 Recalled {len(hits)} passages from this chat ({len(store)} indexed)"
            ),
        }
    return {"error": f"unknown tool {name}", "_status": _event("status", text=f"Unknown tool {name}")}


def _places_in_answer(places: dict[str, dict], answer: str) -> list[dict]:
    """Places the answer actually mentions (by name or maps link), in answer order; if the
    answer names none, the first few found."""
    low = answer.lower()
    hits = []
    for p in places.values():
        pos = low.find(p["name"].lower()) if p["name"] else -1
        if pos < 0 and p.get("maps_url") and p["maps_url"] in answer:
            pos = answer.index(p["maps_url"])
        if pos >= 0 and p.get("lat") is not None:
            hits.append((pos, p))
    hits.sort(key=lambda t: t[0])
    chosen = [p for _, p in hits] or [p for p in places.values() if p.get("lat") is not None][:5]
    unique, names = [], set()
    for p in chosen:  # Google can return several places with the same name
        if p["name"].lower() not in names:
            names.add(p["name"].lower())
            unique.append(p)
    return unique[:15]


async def _read_via_gemini(url: str) -> dict | None:
    """Page text through Gemini's url_context tool, for sites that 403 our scraper."""
    try:
        resp, _ = await generate(
            f"Extract the main content of {url} as plain text: headings, key facts, contacts, "
            "dates, phone numbers and links. No commentary.",
            types.GenerateContentConfig(tools=[types.Tool(url_context=types.UrlContext())], temperature=0),
        )
    except Exception as e:
        print(f"url_context read failed: {e}")
        return None
    text = (resp.text or "").strip()
    return {"url": url, "title": url, "content": text, "truncated": False} if text else None


async def google_search(query: str) -> list[dict]:
    """Fallback when every SearXNG engine is down: Gemini's Google Search grounding.
    Grounding chunks carry redirect URLs; resolve them to the real pages."""
    try:
        resp, _ = await generate(
            f"Search the web for: {query}. Briefly list the most relevant results.",
            types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
        )
        meta = resp.candidates[0].grounding_metadata
        chunks = [c.web for c in (meta.grounding_chunks or []) if c.web][:6] if meta else []
    except Exception as e:
        print(f"google_search fallback failed: {e}")
        return []

    async def resolve(uri: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=6, follow_redirects=False) as c:
                r = await c.get(uri)
                return r.headers.get("location") or uri
        except Exception:
            return uri

    urls = await asyncio.gather(*(resolve(w.uri) for w in chunks))
    summary = (resp.text or "")[:600]
    return [
        {"title": w.title or u, "url": u, "snippet": summary if i == 0 else ""}
        for i, (w, u) in enumerate(zip(chunks, urls))
    ]


async def _extras(messages: list[dict], answer: str, sources: list[dict]) -> dict:
    listing = "\n".join(
        f"[{i}] {s['title']} — {s['url']}\n    {s['snippet'][:200]}" for i, s in enumerate(sources)
    ) or "(none)"
    question = messages[-1]["content"] if messages else ""
    prompt = f"""User question: {question}

Assistant answer:
{answer}

Sources seen during research (by index):
{listing}

Return JSON with:
- suggested_questions: 3 short, natural follow-up questions THIS user would likely ask next
  (written in the user's voice, specific to Southwest Florida).
- resources: up to 5 of the most helpful sources above for the user to visit (prefer official
  and directly useful pages; skip junk/duplicates), each with `index` and a one-line `why`.
  Empty if no sources."""
    resp, _ = await generate(
        prompt,
        types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EXTRAS_SCHEMA,
            temperature=0.3,
        ),
    )
    data = json.loads(resp.text or "{}")
    resources = []
    for r in data.get("resources", []):
        i = r.get("index")
        if isinstance(i, int) and 0 <= i < len(sources):
            s = sources[i]
            resources.append({"url": s["url"], "title": s["title"], "why": r.get("why", "")})
    return {"suggested_questions": data.get("suggested_questions", [])[:4], "resources": resources}


_SUMMARY_INSTRUCTIONS = """Summarize this resource for someone in Southwest Florida.
{focus}
Use markdown: a 1-2 sentence overview, then "Key points" bullets, then "What you can do"
(concrete actions, phone numbers, deadlines, eligibility) if the page has any.
Be faithful to the page; don't add facts."""


async def summarize(url: str, focus: str | None = None, session_id: str | None = None) -> dict:
    instructions = _SUMMARY_INSTRUCTIONS.format(focus=f"Focus on: {focus}" if focus else "")
    try:
        page = await fetch_url(url)
    except FetchError:
        # Site blocks our scraper (403 / bot check) — let Gemini fetch it via url_context.
        resp, _ = await generate(
            f"{instructions}\n\nThe resource: {url}",
            types.GenerateContentConfig(tools=[types.Tool(url_context=types.UrlContext())], temperature=0.2),
        )
        if not (resp.text or "").strip():
            raise
        if session_id:  # no page text to index, so index the summary itself
            _background(_safe_index(get_store(session_id).add_page(url, None, resp.text)))
        return {"url": url, "title": None, "summary": resp.text, "truncated": False}

    if session_id:  # summarized pages become recallable in the chat
        _background(_safe_index(get_store(session_id).add_page(page["url"], page["title"], page["content"])))
    prompt = f"""{instructions}

Title: {page['title']}
URL: {page['url']}
---
{page['content']}"""
    resp, _ = await generate(prompt, types.GenerateContentConfig(temperature=0.2))
    return {"url": page["url"], "title": page["title"], "summary": resp.text or "", "truncated": page["truncated"]}
