# Architecture

## Goal

Build a production-shaped multi-source RAG assistant for Vietnamese/English knowledge bases: files, Markdown, Notion exports, websites, sitemaps, and chat integrations — with retrieval and generation that can be reasoned about and evaluated, not a thin prompt wrapper.

## Services

- **FastAPI API/UI** (`app/main.py`, `app/api/routes.py`): upload, source management, chat, feedback, metrics, Slack slash endpoint, and the `/ws/realtime` WebSocket. Also serves the static UI.
- **Worker** (`app/worker.py`): a standalone asyncio loop that consumes Redis sync jobs (with a PostgreSQL polling fallback), performs source ingestion/reindex, and periodically enqueues sources whose `sync_interval_minutes` is due.
- **Bot runner** (`app/bots/runner.py`): optional Discord and Telegram long-polling adapters. Starts only the adapters whose token is configured; idles forever if neither is set.
- **PostgreSQL**: source metadata, documents, chunks (text mirror for debugging), chat logs, feedback, request metrics, sync jobs.
- **Redis**: worker job queue (`rag:sync-jobs` list) and the realtime pub/sub channel (`rag:realtime-events`). Both degrade gracefully if Redis is unreachable.
- **Qdrant**: one collection (`rag_chunks` by default) holding a named dense vector and a named sparse (BM25) vector per point.
- **AI provider**: Gemini/OpenAI/Groq/OpenAI-compatible chat and embedding providers, all called through the OpenAI Python SDK against an OpenAI-compatible endpoint.

## Data Flow

### File upload

1. `POST /documents/upload` streams the file to disk (25 MB default cap, rejected mid-stream if exceeded) and validates the extension against `SUPPORTED_EXTENSIONS`.
2. API creates a `data_sources` row (`status="running"`).
3. `DocumentParser.parse_many` extracts one or more `ParsedDocument`s — a Notion ZIP can expand into many documents, one per Markdown/HTML/TXT member.
4. `IndexingService` chunks each parsed document, embeds the chunks, upserts them to Qdrant, and writes `documents`/`chunks` rows to PostgreSQL.
5. Source is marked `indexed` or `failed`; a `document.uploaded` event is published for the UI.

### URL / sitemap

1. `POST /documents/ingest-url` creates a `data_sources` row (`source_type` = `web` for a single page, `sitemap` for a sitemap) and a `sync_jobs` row, then pushes the job ID onto the Redis queue.
2. The worker dequeues the job, fetches the page (or resolves the sitemap — including nested `<sitemapindex>` sitemaps — and fetches every same-domain URL up to `max_pages`), and converts each page to a `ParsedDocument` via BeautifulSoup text extraction.
3. Worker chunks/embeds/upserts exactly like the upload path, then updates source status and publishes `source.indexed` or `job.failed`.
4. **Scheduled sync**: every `SCHEDULED_SYNC_CHECK_SECONDS` (default 60s), the worker calls `sources_due_for_sync()`, which selects sources with a non-null `sync_interval_minutes` whose `last_synced_at` is missing or older than the interval, and enqueues a `source_sync` job for each (skipping sources that already have a job in flight).

### Chat

1. UI/API/Bot calls the shared `AskService.ask()`.
2. `HybridRetriever` embeds the question (unless `RETRIEVAL_MODE=sparse`) and calls `QdrantHybridStore.search()`, which runs dense, sparse, or RRF-fused hybrid search depending on `RETRIEVAL_MODE`.
3. If a reranker is configured (`RERANKER_PROVIDER=cohere`), the retrieved chunks are always reordered by it — reranking is controlled purely by `RERANKER_PROVIDER`, independent of `RETRIEVAL_MODE`. The `hybrid_rerank` mode value exists as a self-documenting alias for "hybrid retrieval, reranker on"; it does not change retrieval behavior by itself. See [Retrieval](#retrieval) below.
4. `GroundedAnswerer` applies the no-answer threshold, then calls the configured LLM with a JSON-only prompt (or falls back to a deterministic excerpt-based answer if no provider is configured, or if the provider call raises).
5. `AskService` logs a `chat_logs` row + a `request_metrics` row, and returns the Markdown answer, citations, retrieval trace, token usage, cost, and latency. A `chat.completed` event is published.

## Storage Model

| Table | Purpose |
|---|---|
| `data_sources` | One row per logical source: an uploaded file, a Notion ZIP, a web page, or a sitemap. Tracks `status`, `sync_interval_minutes`, `last_synced_at`, `last_error`. |
| `sync_jobs` | Queued/running/completed/failed ingestion or reindex jobs, linked to a source. |
| `documents` | One indexed document (a file, or one page from a Notion export/website), optionally linked to a source via nullable `source_id`. |
| `chunks` | Chunk text and metadata mirror, for debugging and audit — the retrieval path itself reads from Qdrant payloads, not this table. |
| `chat_logs` | Answer, citations, retrieval trace, tokens, cost, latency for every `/chat` call. |
| `feedback` | Rating/comment/correction linked to a chat log. |
| `request_metrics` | Per-request operational records (latency, tokens, cost) used by `/metrics`; also stores bot channel/user context via `add_request_context`. |

Schema note: `AUTO_CREATE_TABLES=true` (default) runs `Base.metadata.create_all` on startup — that is what actually provisions the schema today. Alembic is wired up (`migrations/env.py`, `alembic.ini`) but `migrations/versions/` has no committed revisions yet, so it is not the live migration path. A small in-code shim (`ensure_lightweight_schema_updates` in `app/db/session.py`) adds the `documents.source_id` column if it's missing, to keep a V1 (pre-multi-source) database working after upgrade.

## Retrieval

Default `RETRIEVAL_MODE=hybrid`:

- Dense vector search catches semantic and multilingual matches.
- BM25 sparse search (FastEmbed `Qdrant/bm25`) catches exact terms, names, IDs, dates, and Vietnamese diacritics that embeddings can blur.
- Qdrant's native RRF fusion (`Fusion.RRF` over two `Prefetch` queries, `prefetch_limit=30` each by default) combines both into one ranked list.

Supported `RETRIEVAL_MODE` values:

- `dense` — dense vector search only.
- `sparse` — BM25 only; skips embedding the query entirely.
- `hybrid` — RRF fusion of dense + sparse (default).
- `hybrid_rerank` — same retrieval as `hybrid`; the name is a label for "intend to rerank", not a distinct code path (see below).

Dense-embedding failure handling: if the embedding call for the query fails and the mode is `hybrid`/`hybrid_rerank` with `RETRIEVAL_SPARSE_FALLBACK=true` (default), the retriever silently drops to sparse-only search for that request instead of failing the chat call.

**Reranker** (`RERANKER_PROVIDER`, default `none`):

- `none` — no-op, chunks keep their retrieval order.
- `cohere` — calls Cohere `/v2/rerank` (`rerank-v3.5` by default) and reorders by `relevance_score`. If `COHERE_API_KEY` is missing or the call fails/raises, it silently falls back to the original order rather than failing the chat call.
- `cross-encoder` — accepted as a config value but not implemented; logs a warning and passes chunks through unchanged. Reserved for a future local cross-encoder model.

Because reranking is gated on `RERANKER_PROVIDER` alone, setting `RETRIEVAL_MODE=dense` with `RERANKER_PROVIDER=cohere` also reranks — there is no restriction tying the reranker to hybrid mode specifically.

**No-answer threshold**: `GroundedAnswerer` short-circuits to a no-answer response whenever there are zero retrieved chunks, or the top chunk's score is below `NO_ANSWER_MIN_SCORE` (default `0.16`). Read this threshold against the *scores your configured mode actually produces*: `dense` mode returns raw cosine similarity (roughly 0-1), `sparse` mode returns BM25-style dot-product scores, and `hybrid`/`hybrid_rerank` return Qdrant's RRF fusion score, which is typically much smaller (RRF sums `1/(k+rank)` across the two prefetch lists, so a chunk ranked first in both lists scores roughly `2/61 ≈ 0.033` with Qdrant's default `k=60`). If you switch retrieval modes, re-tune `NO_ANSWER_MIN_SCORE` against your own corpus rather than assuming the default transfers — this is exactly what [docs/EVALUATION.md](EVALUATION.md) is for.

## Ingestion Pipeline Internals

- **Parsers** (`app/ingestion/parsers.py`): `.txt`/`.md`/`.markdown` are read directly; `.pdf` uses `pypdf` per-page extraction with a Docling fallback if `pypdf` returns no usable pages; `.docx` uses `python-docx` paragraph extraction with the same Docling fallback. `.zip` is treated as a Notion export: it walks every archive member, skips `__MACOSX/`, `.git/`, `attachments/`, and dot-directories, and parses `.md`/`.markdown`/`.html`/`.htm`/`.txt` members into separate documents (one Notion ZIP can become many indexed documents).
- **Mojibake repair**: `repair_mojibake` heuristically detects text that was UTF-8 encoded then mis-decoded as Latin-1 (a common artifact in scraped Vietnamese pages and some PDFs), re-encodes/re-decodes it, and keeps the repaired version only if it scores as *less* mojibake than the original.
- **Markdown sectioning**: `markdown_sections_to_pages` splits a Markdown document on `#`-style headings, so each `DocumentPage` corresponds to one heading section (used for both direct `.md` uploads and Notion exports) — this is what lets citations point at a specific section instead of "the whole file".
- **Chunking** (`app/ingestion/chunking.py`, `MetadataChunker`): splits each page into paragraphs, then greedily packs paragraphs into chunks up to `CHUNK_SIZE_TOKENS` (default 700), carrying a token-based tail overlap (`CHUNK_OVERLAP_TOKENS`, default 120) into the next chunk. A single paragraph larger than the chunk size is force-split by word count. Token counts come from `tiktoken` (`TOKENIZER_MODEL`) with a `len(text.split()) * 1.35` heuristic fallback if `tiktoken` can't resolve the model.
- **Web ingestion** (`app/ingestion/web.py`): sends browser-like headers (User-Agent, Accept-Language, Sec-Fetch-*) to reduce basic bot-blocking, follows redirects, and rejects non-text/HTML content types. Sitemap parsing recurses into `<sitemapindex>` documents and filters `<url>` entries to the requested domain before applying `max_pages`.

## Realtime Channel

Every mutating endpoint and every worker job transition calls `publish_event(settings, event_type, **payload)`, which JSON-encodes the event and publishes it to the Redis channel `rag:realtime-events` — this never raises even if Redis is down (`publish_event` swallows the error and logs at debug level).

`GET /ws/realtime` (an actual FastAPI WebSocket, not SSE) accepts the connection, sends a `connected` event, then relays every message from that Redis channel to the browser as JSON. If Redis pub/sub itself fails after connecting, the socket sends one `realtime.degraded` event and then a `heartbeat` every 20 seconds so the UI's connection indicator can still tell the user realtime updates are paused, without dropping the socket. Events carry a `refresh` array (e.g. `["documents", "sources", "metrics"]`) telling the UI which panels to re-fetch — the payload itself is not the source of truth, it's a signal to re-pull via the normal REST endpoints.

## Citation Metadata

Each citation (`app/generation/answerer.py:citation_from_chunk`) includes:

- `filename`, `document_id`, `chunk_id`, `page`;
- `quote` (first 650 characters of the chunk);
- `score` (the retrieval/rerank score);
- `source_type` (`pdf`/`docx`/`txt`/`markdown`/`notion`/`web`/`sitemap`);
- `source_url` (websites only);
- `source_title`;
- `source_path` (file path within a Notion ZIP, or a Markdown file's own name).

## Failure Modes

- Unsupported upload type: `415`.
- Oversized upload: `413`, partial file is deleted.
- URL fetch error, non-HTML/text content type, or unparsable sitemap XML: the sync job and source are marked `failed` with the error message; nothing is partially indexed.
- Qdrant unavailable at startup: `ensure_collection()` failure is swallowed so the app still serves docs/health; upload and chat will surface a clear error once actually attempted.
- Qdrant dimension mismatch: if the collection already exists with a different dense vector size than the current embedding provider returns, `ensure_collection` raises immediately with an explicit message telling you to match the provider or recreate the collection/volume.
- Redis unavailable: the API still records queued jobs in PostgreSQL (`JobQueue.enqueue` logs a warning and returns); the worker falls back to `next_queued_job()` DB polling; realtime publish/subscribe degrade to heartbeat-only as described above.
- Missing bot tokens: the bot runner idles (no crash); the API and worker remain fully usable.
- LLM provider call fails or returns malformed JSON: `GroundedAnswerer` catches the exception and falls back to a deterministic, clearly-labeled "development answer" built from the top retrieved chunks, so a flaky provider never 500s the chat endpoint.

## Known Gaps (tracked in [CHECKLIST.md](../CHECKLIST.md))

- `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` exist in `Settings` but are not yet read anywhere — Slack auth today is limited to the optional shared-secret `SLACK_VERIFICATION_TOKEN` form field, not Slack's HMAC request signing.
- No committed Alembic revisions; schema changes currently rely on `create_all` plus the lightweight column shim described above.
- `cross-encoder` reranker is a placeholder; only `cohere` is implemented.
