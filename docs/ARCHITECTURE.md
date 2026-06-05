# Architecture

## Goal

Build a production-shaped multi-source RAG assistant for Vietnamese/English knowledge bases: files, Markdown, Notion exports, websites, sitemaps, and chat integrations.

## Services

- FastAPI API/UI: upload, source management, chat, feedback, metrics, Slack slash endpoint.
- Worker: consumes Redis sync jobs and performs source ingestion/reindex.
- Bot runner: optional Discord and Telegram long-polling adapters.
- PostgreSQL: source metadata, documents, chunks, chat logs, feedback, metrics, sync jobs.
- Redis: worker queue.
- Qdrant: dense vectors plus BM25 sparse vectors.
- AI provider: Gemini/OpenAI/Groq/OpenAI-compatible chat and embedding providers.

## Data Flow

File upload:

1. `POST /documents/upload` saves PDF/DOCX/TXT/Markdown/Notion ZIP.
2. API creates a `data_sources` record.
3. Parser extracts one or more parsed documents.
4. Indexing service chunks, embeds, upserts to Qdrant, writes documents/chunks to PostgreSQL.
5. Source is marked `indexed` or `failed`.

URL/sitemap:

1. `POST /documents/ingest-url` creates a source and sync job.
2. API pushes the job ID to Redis.
3. Worker fetches page or sitemap URLs.
4. Worker parses readable text with BeautifulSoup, chunks/embeds/upserts, and updates source status.
5. Scheduled sync is handled by the worker checking sources with `sync_interval_minutes`.

Chat:

1. UI/API/Bot sends a question to shared `AskService`.
2. Retriever embeds the question and runs Qdrant dense/sparse/hybrid search.
3. Optional reranker can reorder candidates.
4. Answerer applies no-answer threshold and grounded prompt.
5. Response returns Markdown answer, citations, retrieval trace, token usage, cost, and latency.

## Storage Model

- `data_sources`: logical source such as uploaded file, Notion ZIP, website, sitemap.
- `sync_jobs`: queued/running/completed/failed ingestion or reindex jobs.
- `documents`: one indexed document/page, optionally linked to a source.
- `chunks`: chunk text and metadata mirror for debugging.
- `chat_logs`: answer, citations, retrieval trace, tokens, cost, latency.
- `feedback`: rating/comment/correction linked to chat.
- `request_metrics`: operational records.

## Retrieval

Default `RETRIEVAL_MODE=hybrid`:

- dense vector search catches semantic and multilingual matches;
- BM25 sparse search catches exact terms, names, IDs, dates, and Vietnamese diacritics;
- Qdrant RRF fusion combines both.

Supported modes:

- `dense`
- `sparse`
- `hybrid`
- `hybrid_rerank`

Optional reranker:

- `RERANKER_PROVIDER=none` by default.
- `RERANKER_PROVIDER=cohere` uses Cohere `/v2/rerank`.
- `cross-encoder` is reserved for a later local model path.

## Citation Metadata

Each citation can include:

- file/document name;
- page or section;
- chunk ID;
- source type;
- source URL;
- source title;
- source path for Markdown/Notion exports.

## Failure Modes

- Unsupported upload type: `415`.
- Oversized upload: `413`.
- URL fetch error: source and job marked `failed`.
- Qdrant unavailable: upload/chat fail clearly, UI and health remain available.
- Redis unavailable: API still records queued jobs in PostgreSQL; worker can fall back to DB polling.
- Missing bot tokens: bot runner idles; API remains usable.
