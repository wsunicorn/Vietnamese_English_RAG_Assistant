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
- [x] Add Redis queue helper (with PostgreSQL polling fallback when Redis is down).
- [x] Add worker service for source sync, scheduled re-sync, and reindex jobs.
- [x] Add `/sources`, `/sources/{source_id}/sync`, `/sources/{source_id}`, `/reindex`.
- [x] Add source-aware citations: type, URL, title, path.
- [x] Add retrieval mode config and optional Cohere reranker hook.
- [x] Add Slack `/ask` endpoint.
- [x] Add Discord and Telegram bot runner modules.
- [x] Add UI source dashboard, URL ingest form, manual sync/delete, reindex all.
- [x] Add parser/job/bot/reranker tests.

## Done - V3 Realtime + UI Polish

- [x] Add `/ws/realtime` WebSocket backed by Redis pub/sub (`publish_event`/`iter_events`), with heartbeat degradation when Redis is unavailable.
- [x] Wire every mutating endpoint and worker job transition to publish a realtime event.
- [x] Rebuild the UI as a landing page + three-panel operator workspace (sources/documents/history rail, chat, evidence drawer with citations + retrieval trace tabs), with a live realtime status indicator and dark/light theme.
- [x] Add chunk-level Vietnamese/mojibake repair for scraped and PDF text.

## Fixed In This Pass

- [x] `HybridRetriever.retrieve` had a dead `if mode == "hybrid_rerank"` branch that duplicated the fallback return — removed; reranking was (and is) actually gated by `RERANKER_PROVIDER` alone, not by `RETRIEVAL_MODE`.
- [x] `fetch_web_documents` tagged single-page web ingestion chunks with `source_type="page"` instead of `"web"`, which didn't match `data_sources.source_type`, the documented citation `source_type` values, or the UI's `.source-pill.web` styling — fixed to derive `web`/`sitemap` from the ingestion mode.
- [x] `citation_from_chunk` had a dead fallback to a `metadata["notion_path"]` key that is never set anywhere in the codebase — removed.
- [x] `ruff check .` reported 45 false-positive/style errors (FastAPI `Depends`/`File` flagged as B008, unsorted imports, `try/except/pass` instead of `contextlib.suppress`) — added `extend-immutable-calls` and `known-first-party` to the ruff config and applied the safe fixes; `ruff check .` is now clean.
- [x] Removed `app/test_scrape.py`, an unrelated scratch script (scrapes an anime-streaming site with `curl_cffi`, which isn't even a declared dependency) that had been accidentally committed inside the `app` package.
- [x] Rewrote README/docs to match the code as it actually behaves (see the Documentation Map in [README.md](README.md)), including documenting the previously-undocumented realtime WebSocket, the real evaluation script's actual field/metric coverage, and the actual UI structure.

## Still To Polish For Portfolio

- [ ] Add screenshots to README.
- [ ] Fill final evaluation result table after running real corpus (see [docs/EVALUATION.md](docs/EVALUATION.md) — no context-precision/recall/faithfulness scorer is wired up yet, only no-answer accuracy, citation presence, and latency).
- [ ] Record 2-4 minute demo video.
- [ ] Add Docker integration test that boots API, worker, Redis, Postgres, Qdrant.
- [ ] Add sample PDF/DOCX binary fixtures if repo size allows.
- [ ] Add optional Playwright ingestion path for JS-heavy sites.
- [ ] Add Slack request signature verification using `SLACK_SIGNING_SECRET` (currently only the legacy `SLACK_VERIFICATION_TOKEN` shared-secret check exists; `SLACK_SIGNING_SECRET`/`SLACK_BOT_TOKEN` are declared but unused).
- [ ] Add a committed Alembic revision for existing deployed databases (schema today is provisioned by `create_all` + a lightweight column-add shim, not a migration chain).
- [ ] Wire `ragas`/`datasets` (already an optional dependency group) into `scripts/evaluate_rag.py`, or a new script, to actually produce context precision/recall/faithfulness numbers.
- [ ] Implement or remove the `cross-encoder` reranker option (currently accepted but a no-op).

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
- [ ] `/ws/realtime` shows a live status change while a source syncs or a chat completes.
