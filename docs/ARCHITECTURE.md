# Architecture

## Goal

Build a document AI assistant that proves full RAG engineering skill: ingestion, metadata, chunking, hybrid retrieval, grounded generation, citations, feedback, metrics, and Dockerized operations.

## Services

- FastAPI app: owns API, demo UI, ingestion orchestration, retrieval orchestration, and answer generation.
- PostgreSQL: stores document metadata, chunk metadata, chat logs, feedback, and metrics.
- Qdrant: stores dense vectors, BM25 sparse vectors, and chunk payloads for hybrid retrieval.
- AI provider: Gemini, Groq, OpenAI, or any OpenAI-compatible gateway provides grounded answer generation. Gemini/OpenAI/custom gateways can also provide embeddings.

## Data Flow

Upload flow:

1. `POST /documents/upload` receives PDF, DOCX, or TXT.
2. File type and size are validated.
3. File is saved under `data/uploads`.
4. Parser extracts text and metadata:
   - TXT: direct UTF-8 read.
   - PDF: page-level `pypdf`, with Docling fallback.
   - DOCX: `python-docx`, with Docling fallback.
5. Chunker creates token-aware chunks with overlap.
6. Provider embedding client creates dense vectors.
7. FastEmbed creates BM25 sparse vectors.
8. Chunks are written to Qdrant with payload metadata.
9. Document and chunk metadata are written to PostgreSQL.

Chat flow:

1. `POST /chat` receives a user question and optional document filters.
2. The question is embedded with the same embedding model.
3. Qdrant runs dense search and sparse BM25 search, then fuses results with reciprocal-rank style hybrid retrieval.
4. The answerer rejects weak evidence using `NO_ANSWER_MIN_SCORE`.
5. If evidence is adequate, the configured LLM provider receives the retrieved context and returns a structured grounded answer.
6. The API returns answer, citations, no-answer flag, usage, cost, and latency.
7. Chat log and request metrics are stored in PostgreSQL.

Feedback flow:

1. `POST /feedback` stores rating, comment, and correction.
2. Feedback later powers eval-set expansion and prompt/retrieval tuning.

## PostgreSQL Tables

- `documents`: uploaded file metadata, language, status, page count, chunk count.
- `chunks`: chunk text and metadata mirror for audit/debug.
- `chat_logs`: question, answer, citations, retrieval trace, tokens, estimated cost, latency.
- `feedback`: rating and correction records linked to chats.
- `request_metrics`: endpoint-level operational metrics.

## Qdrant Collection

Collection: `rag_chunks`

Named vectors:

- `dense`: provider embedding vector, default configured dimension `3072`.
- `sparse`: FastEmbed BM25 sparse vector.

Payload fields:

- `chunk_id`
- `document_id`
- `filename`
- `text`
- `page`
- `section`
- `token_count`
- `metadata`

## Retrieval Strategy

Default retrieval uses hybrid search because bilingual document QA benefits from both:

- dense vectors for semantic matches, paraphrases, and translated intent;
- sparse BM25 for exact terms, numbers, names, legal clauses, IDs, and Vietnamese diacritics.

The v1 pipeline retrieves top candidates from both representations and fuses them in Qdrant. A future reranker can be added after the fused top 20-40 results.

## No-Answer Handling

The system returns no-answer when:

- no chunks are retrieved;
- top retrieval score is below `NO_ANSWER_MIN_SCORE`;
- the model's structured response marks `no_answer=true`.

The answer prompt forbids unsupported facts and requires citation markers. The API removes citations when the final answer is no-answer.

## Failure Modes

- Unsupported file type: `415`.
- File too large: `413`.
- Parsing/indexing failure: document is marked `failed`, endpoint returns `500`.
- Qdrant temporarily unavailable: health and UI still load, upload/chat fail clearly.
- Missing provider key: deterministic fallback lets the app demo locally, but production-quality answers require API config.
- Embedding provider switch: if the new model returns a different vector size, recreate the Qdrant collection or keep the same embedding provider/model for existing data.
