# Evaluation

## Goal

Show that this assistant is stronger than a basic GPT wrapper by measuring retrieval quality, citation quality, answer faithfulness, no-answer behavior, latency, and cost — with numbers, not just a demo.

## Modes To Compare

Set these via `.env` (or per-run overrides) and re-run the same question set:

- Dense-only: `RETRIEVAL_MODE=dense`
- Sparse-only: `RETRIEVAL_MODE=sparse`
- Hybrid: `RETRIEVAL_MODE=hybrid`
- Hybrid + reranker: `RETRIEVAL_MODE=hybrid`, `RERANKER_PROVIDER=cohere`

Note: the reranker is controlled entirely by `RERANKER_PROVIDER`, not by the retrieval mode value — `RETRIEVAL_MODE=hybrid_rerank` behaves identically to `hybrid` unless `RERANKER_PROVIDER=cohere` is also set. You could equally test `dense` + reranker; the four-row table above is simply the combination most worth reporting for a portfolio (see [ARCHITECTURE.md#retrieval](ARCHITECTURE.md#retrieval)).

**Before comparing modes**, re-check `NO_ANSWER_MIN_SCORE` for each one. `dense`/`sparse` return raw similarity scores (roughly 0-1); `hybrid` returns Qdrant's RRF fusion score, which is numerically much smaller (a top-ranked chunk scores around `0.03`, not `0.3`). Using one threshold across all four rows will silently over- or under-trigger no-answer for whichever modes don't match the threshold's scale — track "No-Answer Accuracy" per mode specifically to catch this.

## Dataset Format

`scripts/evaluate_rag.py` reads JSONL from `evals/golden_set.jsonl`. A small starter set already ships in the repo (3 rows: one Vietnamese answerable question, one English answerable question, one Vietnamese out-of-scope question) — treat it as a format example, not a real evaluation set; replace/expand it with rows from your own indexed corpus before drawing conclusions.

Each row's only *required* fields are `id`, `question`, and `should_answer` — those are the only three the script currently reads:

```json
{"id": "leave-policy-1", "question": "...", "should_answer": true}
```

The shipped file also carries `expected_answer`, `expected_document`, `expected_pages`, and `language` per row — useful reference fields for manual grading or a future scorer, but **`scripts/evaluate_rag.py` does not read or score against them today**:

```json
{"id":"vi_demo_001","question":"Tai lieu noi gi ve chinh sach nghi phep?","expected_answer":"Answer should describe the leave policy from the uploaded document.","expected_document":"employee_handbook_vi.pdf","expected_pages":[1],"should_answer":true,"language":"vi"}
```

Expand with:

- Vietnamese policy questions;
- English handbook questions;
- Markdown/Notion export questions;
- website/sitemap questions;
- out-of-scope no-answer questions (`should_answer: false`).

## Running The Built-In Script

```bash
python scripts/evaluate_rag.py --api-url http://localhost:8000 --dataset evals/golden_set.jsonl
```

For each row it calls `POST /chat` with the question and reports, per row and as a summary:

- `no_answer_accuracy` — did `no_answer` match the inverse of `should_answer`?
- `citation_rate_on_answerable` — for rows where `should_answer` is true, did the response include *any* citation? (This is presence, not correctness — it does not check citations against `expected_citations`.)
- `avg_latency_ms` — average `/chat` latency across the run.

This script only needs `httpx`, already a core dependency — no extra install required.

## Metrics Not Yet Automated

`ragas` and `datasets` are declared under the `eval` optional dependency group in `pyproject.toml`, but nothing in the repository imports them yet — there is no wired-up context precision/recall/faithfulness/answer-relevance scorer today. To fill in the rest of the table below, either:

- score `expected_document`/`expected_pages` vs. actual `citations[].filename`/`page` by hand or with a small script, and/or
- wire `evals/golden_set.jsonl` + `/chat` responses into `ragas` yourself (the dependency is there, the integration is not).

Full metric list to eventually cover:

- Context precision.
- Context recall.
- Faithfulness.
- Answer relevance.
- Citation accuracy (does the cited `document_id`/`page`/`source_url` actually contain the claim — stricter than the script's citation-presence check).
- No-answer accuracy (covered by the script above).
- Average latency (covered by the script above, or `avg_chat_latency_ms` from `GET /metrics`).
- Estimated cost (`usage.estimated_cost_usd` per call, only non-zero once `INPUT_COST_PER_1M_TOKENS`/`OUTPUT_COST_PER_1M_TOKENS` are set).

## Result Table Template

| Mode | Context Precision | Context Recall | Citation Accuracy | No-Answer Accuracy | Avg Latency |
|---|---:|---:|---:|---:|---:|
| Dense | TBD | TBD | TBD | TBD | TBD |
| Sparse | TBD | TBD | TBD | TBD | TBD |
| Hybrid | TBD | TBD | TBD | TBD | TBD |
| Hybrid + Reranker | TBD | TBD | TBD | TBD | TBD |

## Demo Acceptance

- Upload Markdown and Notion ZIP.
- Ingest a public documentation page.
- Ingest a sitemap with `max_pages`.
- Ask one Vietnamese and one English question.
- Show citation drawer with file/page or URL/path, and the retrieval trace tab.
- Ask an out-of-scope question and verify no-answer.
- Submit feedback.
- Show metrics and source dashboard.
- Trigger `/ask` through one configured bot or the Slack endpoint.
- Open `/ws/realtime` (or just watch the top-bar indicator) and show a live update while a background sync completes.
