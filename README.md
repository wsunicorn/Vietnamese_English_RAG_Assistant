# Document AI Assistant with Multi-Source RAG, Citations and Chat Integration

Flagship portfolio project: an end-to-end Vietnamese/English knowledge-base assistant for internal documents, Markdown/Notion exports, websites, and sitemaps. It is designed to prove real RAG engineering, not just an LLM wrapper — hybrid retrieval, source-aware citations, a background ingestion worker, a live dashboard, and grounded no-answer behavior.

## What It Solves

Teams often keep knowledge across PDFs, DOCX files, Notion exports, Markdown docs, and internal websites. People waste time searching, asking coworkers, or rereading docs. This app lets users ask questions in Vietnamese or English, returns grounded answers with citations, and says it cannot find an answer when evidence is weak — instead of guessing.

## Current Features

- Upload PDF, DOCX, TXT, Markdown, and Notion export ZIP (multiple pages per ZIP).
- Ingest a single website page or a full sitemap through a Redis-backed worker, with optional scheduled re-sync.
- Parse text and metadata, including page, section, URL, source path, and source type; repair common mojibake (double-encoded UTF-8) in PDFs and web pages.
- Chunk documents by paragraph with token-aware sizing, overlap, and heading-aware Markdown/Notion sections.
- Store dense vectors and BM25 sparse vectors in a single Qdrant collection with named vectors.
- Hybrid retrieval (dense + sparse + Qdrant RRF fusion) with selectable dense-only/sparse-only modes and an optional Cohere reranker.
- Grounded chat endpoint with citation markers (`[C1]`, `[C2]`, ...), retrieval trace, token usage, cost estimate, and no-answer handling.
- A `/ws/realtime` WebSocket channel (backed by Redis pub/sub) that pushes upload/index/sync/chat events to the browser live, with automatic degradation to heartbeat-only mode if Redis is unavailable.
- Feedback endpoint and metrics endpoint.
- Source dashboard UI with manual sync, delete, URL ingestion, compact evidence drawer, chat history, and Markdown answer rendering.
- Optional Slack slash-command endpoint and optional Discord/Telegram bot runners, all sharing the same `AskService` as the UI.
- Docker Compose with FastAPI, worker, bots, PostgreSQL, Qdrant, and Redis.

## Tech Stack

- Python 3.12, FastAPI (incl. WebSocket), Pydantic v2, SQLAlchemy 2.0 async.
- Parsing: pypdf (Docling fallback), python-docx (Docling fallback), BeautifulSoup, custom Markdown/Notion ZIP parsing.
- Retrieval: Qdrant dense+sparse hybrid search with RRF fusion, FastEmbed BM25 (`Qdrant/bm25`), configurable embedding providers.
- Generation: Gemini/OpenAI/Groq/OpenAI-compatible chat providers via the OpenAI SDK, with a deterministic offline fallback answerer.
- Worker: Redis list queue plus PostgreSQL job/source tracking, with automatic DB-polling fallback if Redis is down.
- Realtime: Redis pub/sub relayed to the browser over a native FastAPI WebSocket.
- UI: FastAPI-served static HTML/CSS/vanilla JS (marketing landing page + a three-panel operator workspace).
- Bots: Slack slash-command endpoint, Discord.py, python-telegram-bot.
- Tests: pytest (22 tests covering API, chunking, parsers, providers, jobs, reranking, no-answer behavior).

## Quickstart

1. Copy env:

```bash
cp .env.example .env
```

2. Add a free-friendly provider key:

```env
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
```

3. Run:

```bash
docker compose up --build
```

4. Open:

- UI: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- Qdrant dashboard: <http://localhost:6333/dashboard>

No API key? Leave `LLM_PROVIDER=development` and `EMBEDDING_PROVIDER=hash` — the app still runs end to end with deterministic offline answers and local hash embeddings, which is useful for smoke-testing the pipeline without spending API credits.

## API Surface

- `POST /documents/upload` — upload PDF/DOCX/TXT/Markdown/Notion ZIP.
- `POST /documents/ingest-url` — queue a website page or sitemap for the worker.
- `GET /documents` — list indexed documents.
- `DELETE /documents/{document_id}` — remove a document and its vectors.
- `GET /sources` — list data sources with document/chunk counts and sync status.
- `POST /sources/{source_id}/sync` — queue a manual re-sync.
- `DELETE /sources/{source_id}` — delete a source, its documents, and its vectors.
- `POST /reindex` — queue a re-sync for every source.
- `POST /chat` — ask a grounded question.
- `POST /feedback` — rate an answer.
- `GET /metrics` — aggregate documents/chunks/chats/feedback/tokens/cost.
- `POST /bots/slack/ask` — Slack slash-command endpoint (shares `AskService` with the UI).
- `WS /ws/realtime` — live event stream for the dashboard (upload, sync, chat, job status).

Runnable examples are in [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md).

## Architecture

```text
Landing UI + App Workspace + Bots
      |                          \
      v                           \  WS /ws/realtime <- Redis pub/sub
FastAPI routes -> AskService -> hybrid retrieval -> grounded generation
      |              |              |                    |
      |              |              v                    v
      |              |           Qdrant             Gemini/OpenAI/etc.
      |              v
      |          PostgreSQL: sources, documents, chunks, chat_logs, feedback, metrics
      |
      +-> upload / ingest-url -> data_sources + sync_jobs row -> Redis queue
                                      |
                                      v
                                Worker service (polls Redis, falls back to Postgres)
                                      |
                                      v
                         parse -> chunk -> embed -> Qdrant + Postgres
                                      |
                                      v
                         publish_event() -> Redis pub/sub -> WebSocket clients
```

Details and design rationale: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation Map

| Doc | What it covers |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Services, data flow, storage model, retrieval internals, realtime channel, failure modes |
| [docs/UI_DESIGN.md](docs/UI_DESIGN.md) | The actual built UI: landing page and the three-panel operator workspace |
| [docs/PROVIDERS.md](docs/PROVIDERS.md) | LLM/embedding provider setup, reranker, cost accounting |
| [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md) | curl examples for every endpoint, including the WebSocket |
| [docs/CHAT_INTEGRATIONS.md](docs/CHAT_INTEGRATIONS.md) | Slack, Discord, Telegram wiring and current limitations |
| [docs/EVALUATION.md](docs/EVALUATION.md) | How to compare retrieval modes and score answer quality |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Build phases, for context on how the system evolved |

## Portfolio Deliverables

- README, architecture docs, API examples, evaluation plan.
- Screenshots: upload, web source sync, chat answer, evidence drawer, no-answer, metrics.
- Evaluation table: dense vs sparse vs hybrid vs hybrid+reranker.
- Demo video: 2-4 minutes covering upload, URL/sitemap ingest, Vietnamese question, English question, citations, no-answer, feedback, bot command.

## Development

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev,eval]"
pytest
ruff check .
fastapi dev app/main.py
```

`pytest` and `ruff check .` are expected to pass cleanly on `main`; treat a red run as a real regression, not lint noise.

## Current Status

Use [CHECKLIST.md](CHECKLIST.md) as the source of truth. Do not commit `.env`.
