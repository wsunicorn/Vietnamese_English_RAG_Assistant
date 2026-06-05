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
