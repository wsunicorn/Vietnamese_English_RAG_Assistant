# Evaluation

## Goal

Show that this assistant is stronger than a basic GPT wrapper by measuring retrieval quality, citation quality, answer faithfulness, no-answer behavior, latency, and cost.

## Modes To Compare

- Dense-only: `RETRIEVAL_MODE=dense`
- Sparse-only: `RETRIEVAL_MODE=sparse`
- Hybrid: `RETRIEVAL_MODE=hybrid`
- Hybrid + reranker: `RETRIEVAL_MODE=hybrid_rerank`, `RERANKER_PROVIDER=cohere`

## Dataset Format

Use JSONL in `evals/golden_set.jsonl`:

```json
{"question":"...","expected_answer":"...","expected_citations":["..."],"should_answer":true}
```

Expand with:

- Vietnamese policy questions;
- English handbook questions;
- Markdown/Notion export questions;
- website/sitemap questions;
- out-of-scope no-answer questions.

## Metrics

- Context precision.
- Context recall.
- Faithfulness.
- Answer relevance.
- Citation accuracy.
- No-answer accuracy.
- Average latency.
- Estimated cost.

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
- Show citation drawer with file/page or URL/path.
- Ask an out-of-scope question and verify no-answer.
- Submit feedback.
- Show metrics and source dashboard.
- Trigger `/ask` through one configured bot or Slack endpoint.
