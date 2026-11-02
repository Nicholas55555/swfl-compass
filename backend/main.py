"""SWFL Compass API.  Run:  .venv/Scripts/python -m uvicorn main:app --port 8010"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import agent  # noqa: E402
from scraper import FetchError  # noqa: E402
from searxng import searxng  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        url = await asyncio.to_thread(searxng.ensure_running)
        print(f"SearXNG ready at {url}")
    except Exception as e:  # app still runs; search will retry lazily
        print(f"WARNING: SearXNG not started: {e}")
    yield


app = FastAPI(title="SWFL Compass", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Message(BaseModel):
    role: str
    content: str


class DocTask(BaseModel):
    kind: str  # "itinerary" | "guide"
    days: int | None = None
    base: str | None = None
    interests: list[str] = []
    notes: str | None = None
    topic: str | None = None


class ChatRequest(BaseModel):
    messages: list[Message]
    persona: str | None = None
    session_id: str | None = None
    task: DocTask | None = None


class SummarizeRequest(BaseModel):
    url: str
    focus: str | None = None
    session_id: str | None = None


@app.get("/api/health")
async def health():
    import rag

    return {
        "ok": True,
        "searxng": searxng.base_url,
        "model": agent._last_good or agent.MODEL,
        "rag_sessions": {sid[:8]: len(st) for sid, st in rag._sessions.items()},
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    msgs = [m.model_dump() for m in req.messages]
    return StreamingResponse(
        agent.run_agent(
            msgs, req.persona, req.session_id, req.task.model_dump() if req.task else None
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/summarize")
async def summarize(req: SummarizeRequest):
    try:
        return await agent.summarize(req.url, req.focus, req.session_id)
    except FetchError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
