# Implementation Plan

## Phase 1 - Current V1 Baseline

- FastAPI backend, Docker Compose, PostgreSQL, Qdrant.
- File upload for PDF/DOCX/TXT.
- Metadata-aware chunking.
- Hybrid retrieval.
- Grounded chat, citations, no-answer, feedback, metrics.
- Demo UI and tests.

## Phase 2 - Multi-Source Source Layer

- Add `data_sources` and `sync_jobs`.
- Link documents to sources.
- Keep existing uploaded documents backward compatible through nullable `source_id`.
- Add source list/sync/delete/reindex APIs.

## Phase 3 - Extended Ingestion

- Add Markdown parsing with heading sections.
- Add Notion export ZIP parsing.
- Add website and sitemap ingestion.
- Store URL/path/source title in metadata for citations.

## Phase 4 - Worker And Scheduled Sync

- Add Redis service and worker service.
- API creates jobs and pushes job IDs to Redis.
- Worker processes source sync and reindex jobs.
- Worker periodically enqueues due scheduled sources.

## Phase 5 - Chat Integrations

- Move chat orchestration into `AskService`.
- API, Slack, Discord, and Telegram use the same service.
- Slack is exposed as `/bots/slack/ask`.
- Discord and Telegram run from optional bot runner.

## Phase 6 - Retrieval Evaluation

- Add retrieval modes: dense, sparse, hybrid, hybrid_rerank.
- Add optional Cohere reranker.
- Use eval data to compare retrieval and citation quality.

## Phase 7 - Portfolio Polish

- Add screenshots.
- Run evaluation table.
- Record demo video.
- Add deployment notes for a public Slack slash command URL.

## Phase 8 - Realtime Dashboard And UI Rebuild

- Add Redis pub/sub (`rag:realtime-events`) and a FastAPI `/ws/realtime` WebSocket that relays it to the browser, with heartbeat-only degradation if Redis is unavailable.
- Publish an event from every mutating endpoint and worker job transition (upload, delete, sync queued/running/indexed/failed, chat completed, feedback stored, reindex queued), each carrying a `refresh` list naming which UI panels changed.
- Rebuild the static UI as a marketing landing page plus a three-panel operator workspace (sources/documents/history rail, chat, evidence drawer with citation + retrieval-trace tabs), with a live connection indicator and dark/light theme.
- Add PDF/web-scrape mojibake repair so double-encoded Vietnamese text renders correctly in chunks and citations.

## Phase 9 - Codebase And Documentation Audit

- Fix the retrieval/citation-metadata bugs found during a full read-through (dead `hybrid_rerank` branch, `source_type` mismatch on single-page web ingestion, dead `notion_path` fallback key).
- Clean up lint configuration so `ruff check .` reflects real issues instead of FastAPI-idiom false positives.
- Remove an accidentally-committed, unrelated scratch script from the `app` package.
- Rewrite README and `docs/*.md` to match verified current behavior — including previously-undocumented features (the realtime channel, the actual built UI) and previously-overstated ones (the evaluation script's real metric coverage).
