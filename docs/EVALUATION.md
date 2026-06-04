# Evaluation

## Goal

Show that this assistant is not just a demo wrapper. It should be measured for retrieval quality, answer grounding, citation accuracy, and no-answer behavior in Vietnamese and English.

## Golden Set Format

Use JSONL rows:

```json
{
  "id": "vi_policy_001",
  "question": "Nhan vien duoc nghi phep nam bao nhieu ngay?",
  "expected_answer": "Nhan vien duoc nghi 12 ngay phep nam.",
  "expected_document": "employee_handbook_vi.pdf",
  "expected_pages": [3],
  "should_answer": true,
  "language": "vi"
}
```

For no-answer rows:

```json
{
  "id": "no_answer_001",
  "question": "CEO cua OpenAI hien tai la ai?",
  "expected_answer": null,
  "expected_document": null,
  "expected_pages": [],
  "should_answer": false,
  "language": "vi"
}
```

## Metrics

- Context precision: retrieved chunks are relevant.
- Context recall: expected evidence appears in retrieved chunks.
- Faithfulness: final answer is supported by retrieved context.
- Response relevancy: answer directly addresses the question.
- Citation accuracy: cited document/page/chunk contains the claim.
- No-answer accuracy: model refuses when documents do not contain the answer.
- Latency: upload indexing time and chat response time.
- Cost: token and estimated USD cost per chat.

## Baseline Matrix

| Variant | Context Precision | Context Recall | Faithfulness | No-Answer Accuracy | P95 Latency |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dense only | TBD | TBD | TBD | TBD | TBD |
| Hybrid Qdrant | TBD | TBD | TBD | TBD | TBD |
| Hybrid + reranker | TBD | TBD | TBD | TBD | TBD |

## How To Run

1. Start the stack.
2. Upload the evaluation corpus.
3. Run:

```bash
python scripts/evaluate_rag.py --api-url http://localhost:8000 --dataset evals/golden_set.jsonl
```

4. Paste the final table into this document.

## Acceptance Targets

- Context recall: at least 0.85 on the first curated corpus.
- Faithfulness: at least 0.90 after prompt tuning.
- No-answer accuracy: at least 0.90.
- Citation accuracy: at least 0.90.
- P95 chat latency: under 8 seconds for small corpora with the configured LLM provider.
