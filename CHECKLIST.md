# Project Checklist

## 1. Foundation

- [x] Create project structure.
- [x] Add `pyproject.toml`.
- [x] Add `.env.example`.
- [x] Add `Dockerfile`.
- [x] Add `docker-compose.yml`.
- [x] Add Alembic configuration shell.

## 2. Backend API

- [x] Add FastAPI app.
- [x] Add health endpoint.
- [x] Add document upload endpoint.
- [x] Add document list endpoint.
- [x] Add document delete endpoint.
- [x] Add chat endpoint.
- [x] Add feedback endpoint.
- [x] Add metrics endpoint.

## 3. Ingestion

- [x] Validate PDF/DOCX/TXT uploads.
- [x] Parse TXT.
- [x] Parse PDF with page metadata when available.
- [x] Parse DOCX.
- [x] Add Docling fallback.
- [x] Add metadata-aware chunking.
- [x] Store chunk metadata.

## 4. Retrieval

- [x] Add provider-agnostic embedding client.
- [x] Add local deterministic embedding fallback.
- [x] Add Qdrant collection setup.
- [x] Add FastEmbed BM25 sparse vectors.
- [x] Add hybrid dense + sparse retrieval.
- [ ] Add optional reranker.
- [ ] Add dense-only vs hybrid evaluation switch.

## 5. Generation

- [x] Add grounded bilingual prompt.
- [x] Add provider-agnostic LLM integration.
- [x] Add JSON structured output.
- [x] Add citation shaping.
- [x] Add no-answer gate.
- [x] Add token/cost logging.

## 6. UI

- [x] Add FastAPI-served demo UI.
- [x] Add upload panel.
- [x] Add document list.
- [x] Add chat panel.
- [x] Add citation panel.
- [x] Add metrics strip.
- [x] Add feedback controls.
- [x] Add responsive layout.

## 7. Testing

- [x] Add unit tests for chunking.
- [x] Add unit tests for no-answer behavior.
- [x] Add unit tests for cost estimation.
- [x] Add health endpoint smoke test.
- [ ] Add Docker integration test for Qdrant/PostgreSQL.
- [ ] Add sample PDF/DOCX fixture tests.

## 8. Portfolio

- [x] Add README.
- [x] Add architecture doc.
- [x] Add implementation plan.
- [x] Add API examples.
- [x] Add UI design doc.
- [x] Add evaluation doc.
- [ ] Add screenshots.
- [ ] Record 2-4 minute demo video.
- [ ] Fill final evaluation results table.
