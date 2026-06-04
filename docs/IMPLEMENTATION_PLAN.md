# Implementation Plan

## Phase 1: Project Foundation

- Create Python project metadata and dependency groups.
- Add Dockerfile and Docker Compose for API, PostgreSQL, and Qdrant.
- Add `.env.example` with provider, model, retrieval, database, and cost settings.
- Add FastAPI app shell, static UI mount, health endpoint, and OpenAPI metadata.

Acceptance:

- `docker compose up --build` starts API, PostgreSQL, and Qdrant.
- `GET /healthz` returns app status.

## Phase 2: Ingestion

- Add upload endpoint with PDF/DOCX/TXT validation and file-size limits.
- Parse TXT directly, PDF page-by-page with `pypdf`, DOCX with `python-docx`, and use Docling fallback.
- Implement metadata-aware chunking with token-aware size and overlap.
- Store document and chunk audit metadata in PostgreSQL.

Acceptance:

- Uploading TXT creates at least one chunk.
- Uploading PDF preserves page numbers when extractable.
- Failed parsing marks document status as `failed`.

## Phase 3: Hybrid Retrieval

- Create Qdrant collection with named dense and sparse vectors.
- Generate dense vectors through the configured embedding provider.
- Generate sparse BM25 vectors through FastEmbed.
- Upsert chunk payloads into Qdrant.
- Retrieve with dense + sparse prefetch and Qdrant fusion.

Acceptance:

- Chat retrieval returns chunk payloads with document ID, filename, page, text, and score.
- Document filters restrict retrieval to selected documents.

## Phase 4: Grounded Generation

- Add grounded bilingual prompt.
- Use provider-agnostic OpenAI-compatible chat completion with JSON output instructions.
- Return answer, citations, confidence, no-answer flag, retrieval trace, tokens, cost, and latency.
- Add deterministic fallback for local demos without API key.

Acceptance:

- In-document questions return cited answers.
- Out-of-document questions return no-answer.
- Citations reference real chunks and page metadata.

## Phase 5: Product Loop

- Add feedback endpoint and metrics endpoint.
- Add chat log and request metrics persistence.
- Add demo UI for upload, documents, chat, citations, feedback, and metrics.
- Add docs, API examples, evaluation guide, checklist, and demo-video script notes.

Acceptance:

- Metrics update after upload/chat/feedback.
- Feedback is stored against a chat ID.
- README quickstart reproduces the demo.

## Phase 6: Evaluation And Polish

- Add bilingual golden set.
- Run baseline evals for dense-only, hybrid, and hybrid + reranker.
- Track context precision, context recall, faithfulness, response relevance, citation accuracy, and no-answer accuracy.
- Record screenshots and a 2-4 minute demo video.

Acceptance:

- `docs/EVALUATION.md` contains measured results.
- Portfolio README includes screenshots and final case-study narrative.
