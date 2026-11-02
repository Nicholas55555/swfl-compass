# 🧭 SWFL Compass

**AI for SWFL** (FGCU AI Day H{AI}ckathon): an agentic guide for people who live, study, work in,
or visit Southwest Florida.

![SWFL Compass demo](docs/demo/swfl-compass-demo.gif)

▶️ **[Full demo video (MP4, 1 min)](docs/demo/swfl-compass-demo.mp4)** · 📊 **[Presentation (PPTX)](presentation/SWFL-Compass.pptx)** · 📂 **[Sample outputs](docs/samples/)**

Ask a question and the agent searches the web, reads pages, checks real places on Google Maps,
answers with links and a map, points you to the most helpful resources, summarizes any of them on
request, and suggests what to ask next. It can also **plan a day-by-day itinerary** or **write a
practical guide** that you can download as Markdown or print to PDF.

## Screenshots

| Ask anything, as a resident, student, worker or visitor | A researched, sourced answer |
|---|---|
| ![Welcome screen](docs/demo/01-welcome.png) | ![Answer](docs/demo/03-answer.png) |
| **Real places from Google Maps, pinned on a map** | **Helpful resources with one-click summaries** |
| ![Map](docs/demo/04-map.png) | ![Resource summary](docs/demo/05-resources-summary.png) |
| **Itinerary builder** | **Generated itinerary document** |
| ![Itinerary builder](docs/demo/07-itinerary-builder.png) | ![Itinerary](docs/demo/08-itinerary-doc.png) |
| **Itinerary places with ratings and open-now** | **Personas change the starter questions** |
| ![Itinerary map](docs/demo/10-itinerary-map.png) | ![Student persona](docs/demo/12-student-welcome.png) |
| **Follow-up uses RAG memory: “Found 5 relevant passages”** | **Guides with checklists** |
| ![RAG follow-up steps](docs/demo/13-followup-rag-steps.png) | ![Guide](docs/demo/15-guide-doc.png) |

**On phones**

<img src="docs/demo/11-mobile.png" alt="Mobile welcome" width="230"> <img src="docs/demo/16-mobile-answer.png" alt="Mobile answer" width="230"> <img src="docs/demo/17-mobile-map.png" alt="Mobile map" width="230">

**Exported documents** (real PDFs in [`docs/samples/`](docs/samples/))

<a href="docs/samples/itinerary-3-day-fort-myers-family.pdf"><img src="docs/samples/previews/itinerary-3-day-fort-myers-family-p1.png" alt="Itinerary PDF" width="230"></a> <a href="docs/samples/guide-hurricane-prep-renters-lee-county.pdf"><img src="docs/samples/previews/guide-hurricane-prep-renters-lee-county-p1.png" alt="Guide PDF" width="230"></a> <a href="docs/samples/answer-fgcu-to-downtown-without-car.pdf"><img src="docs/samples/previews/answer-fgcu-to-downtown-without-car-p1.png" alt="Answer PDF" width="230"></a> <a href="docs/samples/summary-fwc-red-tide-status.pdf"><img src="docs/samples/previews/summary-fwc-red-tide-status-p1.png" alt="Summary PDF" width="230"></a>

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

## Sample outputs
Real, unedited results from the app (Markdown + PDF + raw JSON) in [`docs/samples/`](docs/samples/):

- 🗺️ **[3-day Fort Myers family itinerary (PDF)](docs/samples/itinerary-3-day-fort-myers-family.pdf)**: 9 Google-verified places with ratings and Maps links
- 📄 **[Hurricane prep guide for Lee County renters (PDF)](docs/samples/guide-hurricane-prep-renters-lee-county.pdf)**: checklists, official contacts, sources
- 💬 **[FGCU → downtown Fort Myers without a car (PDF)](docs/samples/answer-fgcu-to-downtown-without-car.pdf)**: chat answer with resources and follow-ups
- ✨ **[FWC red tide status summary (PDF)](docs/samples/summary-fwc-red-tide-status.pdf)**: one-click resource summary

Regenerate with the app running: `backend/.venv/Scripts/python scripts/export_samples.py`.

## Presentation & demo
- `presentation/SWFL-Compass.pptx`: 18-slide hackathon deck with speaker notes: problem, solution, embedded demo video (slide 4), a feature tour (personas, live research, Google Maps places, resources, RAG memory, itinerary builder, real itinerary/guide PDF outputs, exports, mobile), architecture and what's next.
  Rebuild with `cd presentation && npm install && npm run build`.
- `docs/demo/`: demo video (MP4 + GIF) and screenshots, recorded from the running app by
  `scripts/record_demo.py` and `scripts/capture_features.py` (Playwright). Re-record with the app running:
  `backend/.venv/Scripts/python -m pip install playwright imageio-ffmpeg && backend/.venv/Scripts/python -m playwright install chromium && backend/.venv/Scripts/python scripts/record_demo.py`

## Run with Docker (recommended)
Only prerequisite: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with Compose v2).

```bash
git clone https://github.com/Nicholas55555/swfl-compass.git   # or download the release zip
cd swfl-compass
cp .env.example .env          # Windows: copy .env.example .env
# edit .env: set GEMINI_API_KEY (and optionally GOOGLE_MAPS_API_KEY)
docker compose up -d --build
```
Open **http://localhost:8080**. Stop with `docker compose down`.

Three containers: `frontend` (React build served by nginx, which proxies `/api` with streaming
intact), `backend` (FastAPI agent) and `searxng` (pinned search engine, internal only).

**API keys are Docker configuration.** Compose reads them from `.env` next to `docker-compose.yml`,
or from your shell / CI environment, which take precedence:

```bash
GEMINI_API_KEY=your-key GOOGLE_MAPS_API_KEY=your-maps-key docker compose up -d
```

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | LLM + embeddings ([get one](https://aistudio.google.com/apikey)). Compose refuses to start without it |
| `GOOGLE_MAPS_API_KEY` | optional | Verified places + map pins (enable **Places API (New)**) |
| `APP_PORT` | optional | Host port for the UI (default `8080`) |
| `GEMINI_MODEL`, `GEMINI_FALLBACKS` | optional | Model overrides |

Changed a key? Run `docker compose up -d` again (no rebuild needed).

**Offline / no Docker Hub:** `docker load -i searxng/searxng-image.tar` first, if you have the saved image.

## Run locally for development (Windows)
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

### Keys for local development (`backend/.env`)
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
