# Document AI Assistant with Multi-Source RAG, Citations and Chat Integration

Flagship portfolio project: an end-to-end Vietnamese/English knowledge-base assistant for internal documents, Markdown/Notion exports, websites, and sitemaps. It is designed to prove real RAG engineering, not just an LLM wrapper.

## What It Solves

Teams often keep knowledge across PDFs, DOCX files, Notion exports, Markdown docs, and internal websites. People waste time searching, asking coworkers, or rereading docs. This app lets users ask questions in Vietnamese or English, returns grounded answers with citations, and says it cannot find an answer when evidence is weak.

## Current Features

- Upload PDF, DOCX, TXT, Markdown, and Notion export ZIP.
- Ingest website pages and sitemaps through a Redis-backed worker.
- Parse text and metadata, including page, section, URL, source path, and source type.
- Chunk documents with metadata.
- Store dense vectors and BM25 sparse vectors in Qdrant.
- Hybrid retrieval with optional dense/sparse eval modes and optional Cohere reranker.
- Grounded chat endpoint with citations and no-answer handling.
- Feedback endpoint and metrics endpoint.
- Source dashboard UI with manual sync, delete, URL ingestion, compact evidence drawer, and Markdown answer rendering.
- Optional Slack slash command endpoint and optional Discord/Telegram bot runners.
- Docker Compose with FastAPI, worker, bots, PostgreSQL, Qdrant, and Redis.

## Tech Stack

- Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async.
- Parsing: Docling fallback, pypdf, python-docx, BeautifulSoup, Markdown/Notion ZIP parsing.
- Retrieval: Qdrant dense+sparse hybrid search, FastEmbed BM25, configurable embedding providers.
- Generation: Gemini/OpenAI/Groq/OpenAI-compatible chat providers.
- Worker: Redis queue plus PostgreSQL sync job tracking.
- UI: FastAPI-served HTML/CSS/vanilla JS.
- Bots: Slack slash endpoint, Discord.py, python-telegram-bot.
- Tests: pytest.

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

## API Surface

- `POST /documents/upload`
- `POST /documents/ingest-url`
- `GET /documents`
- `GET /sources`
- `POST /sources/{source_id}/sync`
- `DELETE /sources/{source_id}`
- `DELETE /documents/{document_id}`
- `POST /reindex`
- `POST /chat`
- `POST /feedback`
- `GET /metrics`
- `POST /bots/slack/ask`

Runnable examples are in [docs/API_EXAMPLES.md](docs/API_EXAMPLES.md).

## Architecture

```text
UI / API / Bots
      |
      v
FastAPI routes -> AskService -> hybrid retrieval -> grounded generation
      |              |              |                    |
      |              |              v                    v
      |              |           Qdrant             Gemini/OpenAI/etc.
      |              v
      |          PostgreSQL logs/feedback/metrics
      |
      +-> upload / ingest-url -> source/job record -> Redis queue
                                      |
                                      v
                                Worker service
                                      |
                                      v
                         parse -> chunk -> embed -> Qdrant/Postgres
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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

## Current Status

Use [CHECKLIST.md](CHECKLIST.md) as the source of truth. Do not commit `.env`.
