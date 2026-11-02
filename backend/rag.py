"""Per-chat RAG: an in-memory vector store over everything the agent has seen.

Each chat session gets its own `VectorStore`. Pages the agent reads are chunked and
embedded with Gemini embeddings; search-result snippets are indexed too. Two uses:

- `read_page` indexes the WHOLE page, then hands the model only the chunks relevant
  to the question (instead of truncating long pages at a fixed char count).
- The `recall` tool lets follow-up questions and document generation (guides,
  itineraries) reuse earlier research without searching the web again.

Plain numpy cosine similarity — a chat's corpus is a few hundred chunks at most, so a
vector DB would be overhead, not help.
"""

from __future__ import annotations

import asyncio
import os
from collections import OrderedDict

import numpy as np
from google.genai import types

EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200
MAX_SESSIONS = 100


def chunk_text(text: str) -> list[str]:
    """Paragraph-aware chunks of ~CHUNK_CHARS with a little overlap."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if len(cur) + len(p) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = cur[-CHUNK_OVERLAP:]
        cur = f"{cur}\n{p}" if cur else p
        while len(cur) > CHUNK_CHARS * 1.5:  # one giant paragraph
            chunks.append(cur[:CHUNK_CHARS])
            cur = cur[CHUNK_CHARS - CHUNK_OVERLAP :]
    if cur.strip():
        chunks.append(cur)
    return chunks


async def embed(texts: list[str], task: str) -> np.ndarray:
    """L2-normalized embeddings, batched (the API takes up to 100 per call)."""
    from agent import clients  # shared client pool / key

    client = clients()[0]
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):
        resp = await client.aio.models.embed_content(
            model=EMBED_MODEL,
            contents=texts[i : i + 100],
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=EMBED_DIM),
        )
        out.extend(e.values for e in resp.embeddings)
    arr = np.asarray(out, dtype=np.float32)
    return arr / (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-8)


class VectorStore:
    def __init__(self) -> None:
        self.chunks: list[dict] = []  # {text, url, title, kind}
        self.vectors = np.zeros((0, EMBED_DIM), dtype=np.float32)
        self.indexed_urls: set[str] = set()
        self._lock = asyncio.Lock()

    def __len__(self) -> int:
        return len(self.chunks)

    async def _add(self, items: list[dict]) -> None:
        if not items:
            return
        vecs = await embed([it["text"] for it in items], "RETRIEVAL_DOCUMENT")
        async with self._lock:
            self.chunks.extend(items)
            self.vectors = np.vstack([self.vectors, vecs])

    async def add_page(self, url: str, title: str | None, text: str) -> int:
        key = f"page:{url}"
        if key in self.indexed_urls:
            return 0
        self.indexed_urls.add(key)
        items = [
            {"text": c, "url": url, "title": title or url, "kind": "page"} for c in chunk_text(text)
        ]
        await self._add(items)
        return len(items)

    async def add_snippets(self, results: list[dict]) -> None:
        items = []
        for r in results:
            key = f"snip:{r['url']}"
            if key in self.indexed_urls or not r.get("snippet"):
                continue
            self.indexed_urls.add(key)
            items.append(
                {"text": f"{r['title']}\n{r['snippet']}", "url": r["url"], "title": r["title"], "kind": "snippet"}
            )
        await self._add(items)

    async def search(self, query: str, k: int = 6, url: str | None = None) -> list[dict]:
        if not self.chunks:
            return []
        q = (await embed([query], "RETRIEVAL_QUERY"))[0]
        scores = self.vectors @ q
        order = np.argsort(-scores)
        hits = []
        for i in order:
            c = self.chunks[int(i)]
            if url and c["url"] != url:
                continue
            hits.append({**c, "score": round(float(scores[i]), 3)})
            if len(hits) >= k:
                break
        return hits


_sessions: OrderedDict[str, VectorStore] = OrderedDict()


def get_store(session_id: str | None) -> VectorStore:
    """The chat's store (LRU-capped). No session id → a throwaway store."""
    if not session_id:
        return VectorStore()
    store = _sessions.get(session_id)
    if store is None:
        store = _sessions[session_id] = VectorStore()
        while len(_sessions) > MAX_SESSIONS:
            _sessions.popitem(last=False)
    _sessions.move_to_end(session_id)
    return store
