# Project Checklist

## Done - V1 Foundation

- [x] FastAPI app, static UI, health endpoint.
- [x] PostgreSQL metadata tables for documents, chunks, chat logs, feedback, metrics.
- [x] Qdrant collection with dense and BM25 sparse vectors.
- [x] Provider-agnostic Gemini/OpenAI/Groq/OpenAI-compatible LLM and embedding clients.
- [x] Upload PDF, DOCX, TXT.
- [x] Parse, chunk, embed, upsert, and store metadata.
- [x] Hybrid retrieval and grounded chat with citations.
- [x] No-answer handling.
- [x] Feedback and metrics endpoints.
- [x] Dockerfile and Docker Compose.
- [x] Pytest suite.

## Done - V2 Multi-Source Upgrade

- [x] Add `data_sources` and `sync_jobs` models.
- [x] Add Markdown upload support.
- [x] Add Notion export ZIP parsing.
- [x] Add URL/sitemap ingestion endpoint.
- [x] Add Redis queue helper.
- [x] Add worker service for source sync and reindex jobs.
- [x] Add `/sources`, `/sources/{source_id}/sync`, `/sources/{source_id}`, `/reindex`.
- [x] Add source-aware citations: type, URL, title, path.
- [x] Add retrieval mode config and optional Cohere reranker hook.
- [x] Add Slack `/ask` endpoint.
- [x] Add Discord and Telegram bot runner modules.
- [x] Add UI source dashboard, URL ingest form, manual sync/delete, reindex all.
- [x] Add parser/job/bot/reranker tests.

## Still To Polish For Portfolio

- [ ] Add screenshots to README.
- [ ] Fill final evaluation result table after running real corpus.
- [ ] Record 2-4 minute demo video.
- [ ] Add Docker integration test that boots API, worker, Redis, Postgres, Qdrant.
- [ ] Add sample PDF/DOCX binary fixtures if repo size allows.
- [ ] Add optional Playwright ingestion path for JS-heavy sites.
- [ ] Add Slack request signature verification using `SLACK_SIGNING_SECRET`.
- [ ] Add production Alembic revision for existing deployed databases.

## Acceptance Checklist

- [ ] `docker compose up --build` starts API, worker, bots, PostgreSQL, Qdrant, Redis.
- [ ] Upload PDF/DOCX/TXT/Markdown works.
- [ ] Upload Notion ZIP indexes multiple pages.
- [ ] Website page ingestion creates a queued source and worker indexes it.
- [ ] Sitemap ingestion respects same-domain and `max_pages`.
- [ ] Chat answer cites file/page or URL/path.
- [ ] Out-of-scope question returns no-answer.
- [ ] Source sync and source delete work from UI.
- [ ] Metrics update after chat.
- [ ] Bot `/ask` command returns compact citations when configured.
