# 🧭 SWFL Compass

**AI for SWFL** (FGCU AI Day H{AI}ckathon) — an agentic guide for people who live, study, work in,
or visit Southwest Florida.

Ask a question and the agent searches the web, reads pages, checks real places on Google Maps,
answers with links and a map, points you to the most helpful resources, summarizes any of them on
request, and suggests what to ask next. It can also **plan a day-by-day itinerary** or **write a
practical guide** that you can download as Markdown or print to PDF.

## Features
- **Agentic research**: Gemini function-calling loop. Each step streams live to the UI
  ("🔎 Searched…", "📍 Found 5 places…", "📄 Read…").
- **Verified places + map**: Google Places API (New) supplies real addresses, ratings, open-now
  status and Maps links. Places mentioned in the answer are pinned on an interactive map.
- **Helpful resources**: up to 5 links, chosen only from pages the agent actually saw
  (no invented URLs). Each has **✨ Summarize**, **Open** and **Ask about it**.
- **Suggested questions**: 3 follow-ups written in the user's voice.
- **Personas**: resident / student / worker / visitor tailor the advice and starter questions.
- **Documents**: 🗺️ itinerary (days, home base, interests) and 📄 guide (any topic, or "this
  conversation"), with ⬇ Download .md, 🖨 Print / Save PDF and 📋 Copy.
- **RAG memory**: every chat has its own vector store, so follow-ups and documents build on
  earlier research.

## Architecture
```
frontend/ (React + Vite)  ──SSE──▶  backend/ (FastAPI)
                                     ├─ agent.py    Gemini tool loop: web_search · read_page · find_places · recall
                                     ├─ rag.py      per-chat vector store (Gemini embeddings + numpy cosine)
                                     ├─ maps.py     Google Places API (New) text search
                                     ├─ searxng.py  SearXNG Docker lifecycle + HTML search
                                     └─ scraper.py  page/PDF text extraction
searxng/  settings.yml (+ optional saved image) — the search engine this app runs
```
- **Search**: self-hosted SearXNG, auto-started by the backend in Docker. The image is pinned
  (`searxng/searxng:2025.7.19-b95a3e9`) and loaded from `searxng/searxng-image.tar` when present,
  so it works without Docker Hub. Public DNS and short engine suspensions make it hold up on flaky
  venue Wi-Fi. If SearXNG returns nothing, search falls back to Gemini Google Search grounding.
- **Reading**: our scraper first; if a site blocks it (403 / bot check), Gemini `url_context`
  reads the page instead. Long pages are indexed in full and the model gets the most relevant
  passages, not a truncated page.
- **RAG**: chunks of pages and search snippets are embedded with `gemini-embedding-001` (768-d).
  Each turn auto-retrieves relevant earlier passages into the prompt; the `recall` tool lets the
  agent search them explicitly.
- **Resilience / cost**: cheapest model first (`gemini-3.1-flash-lite`) with fallbacks on
  overload; retries on empty or malformed responses; if research fails mid-loop, the agent answers
  from what it has gathered.

## Run (Windows)
Prereqs: Python 3.12, Node 20, Docker Desktop running.

**One click:** run `start.bat`. On first run it creates the venv, installs packages and opens
`backend/.env` for your keys. Run it again after saving the keys.

**Manual:**
```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY and GOOGLE_MAPS_API_KEY
.venv/Scripts/python run.py # http://localhost:8010 (auto-starts the SearXNG container)

# frontend (new terminal)
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

**Offline SearXNG image (optional):** `docker save searxng/searxng:2025.7.19-b95a3e9 -o searxng/searxng-image.tar`.
The backend loads it automatically if the image isn't present. It's gitignored (~65 MB).

**Run SearXNG yourself (optional):** `docker compose up -d`, then set
`SEARXNG_BASE_URL=http://localhost:8888` in `backend/.env`.

### Keys (`backend/.env`)
| Variable | Needed for |
|---|---|
| `GEMINI_API_KEY` | everything (LLM + embeddings) |
| `GOOGLE_MAPS_API_KEY` | verified places + map pins (enable **Places API (New)**) |
| `GEMINI_MODEL`, `GEMINI_FALLBACKS` | optional model overrides |

## AI tools / APIs used
- **Google Gemini API**: `gemini-3.1-flash-lite` (fallbacks `gemini-3-flash-preview`,
  `gemini-3.5-flash-lite`). Uses function calling, JSON mode, `url_context` and Google Search grounding.
- **Gemini Embeddings**: `gemini-embedding-001`, for the per-chat vector store.
- **Google Maps Places API (New)**: Text Search.
- **SearXNG**: open-source metasearch, self-hosted.
- **OpenStreetMap** tiles via **Leaflet**: map display.
- **Claude Code**: development assistant.

> Answers are AI-generated. For emergencies, evacuations and closures, always check official
> sources (Lee/Collier/Charlotte County EM, NWS, FWC).
