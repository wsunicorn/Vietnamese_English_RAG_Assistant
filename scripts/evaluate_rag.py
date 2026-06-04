import argparse
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight RAG evaluation set.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--dataset", default="evals/golden_set.jsonl")
    args = parser.parse_args()

    rows = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line]
    results = []
    with httpx.Client(base_url=args.api_url, timeout=60) as client:
        for row in rows:
            response = client.post("/chat", json={"question": row["question"]})
            response.raise_for_status()
            payload = response.json()
            should_answer = bool(row["should_answer"])
            no_answer_correct = payload["no_answer"] is (not should_answer)
            citation_present = bool(payload["citations"])
            results.append(
                {
                    "id": row["id"],
                    "should_answer": should_answer,
                    "no_answer": payload["no_answer"],
                    "no_answer_correct": no_answer_correct,
                    "citation_present": citation_present,
                    "latency_ms": payload["latency_ms"],
                }
            )

    total = len(results) or 1
    no_answer_accuracy = sum(item["no_answer_correct"] for item in results) / total
    cited_answer_rows = [item for item in results if item["should_answer"]]
    citation_rate = (
        sum(item["citation_present"] for item in cited_answer_rows) / len(cited_answer_rows)
        if cited_answer_rows
        else 0
    )
    avg_latency = sum(item["latency_ms"] for item in results) / total

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    print()
    print("Summary")
    print(f"- no_answer_accuracy: {no_answer_accuracy:.2f}")
    print(f"- citation_rate_on_answerable: {citation_rate:.2f}")
    print(f"- avg_latency_ms: {avg_latency:.0f}")


if __name__ == "__main__":
    main()
