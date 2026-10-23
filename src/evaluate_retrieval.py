"""Measure retrieval: is the right document in the top 3 for each ticket?

Run: uv run python src/evaluate_retrieval.py
"""

import json
from pathlib import Path
from statistics import mean
from typing import Any

from retrieval import embed, nearest, open_synced_pool, query_text
from stats import wilson_interval
from tickets import DATASETS, TICKETS_PATH, load_tickets

EXPECTED_PATH = TICKETS_PATH.parent / "expected_docs.jsonl"
RESULTS_PATH = Path(__file__).resolve().parent.parent / "eval" / "retrieval_results.json"
K = 3


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """hit@1 and hit@3 with their 95% intervals, over the tickets a document really answers."""
    answerable = [r for r in rows if r["expected"] != "none"]
    unanswerable = [r for r in rows if r["expected"] == "none"]
    hits1, hits3 = sum(r["hit1"] for r in answerable), sum(r["hit3"] for r in answerable)
    return {
        "answerable": len(answerable),
        "hit@1": hits1 / len(answerable),
        "hit@1_ci": wilson_interval(hits1, len(answerable)),
        "hit@3": hits3 / len(answerable),
        "hit@3_ci": wilson_interval(hits3, len(answerable)),
        "top_score_answerable": [
            round(min(r["top_score"] for r in answerable), 3),
            round(mean(r["top_score"] for r in answerable), 3),
        ],
        "top_score_none": [
            round(mean(r["top_score"] for r in unanswerable), 3),
            round(max(r["top_score"] for r in unanswerable), 3),
        ],
        "misses": [r["id"] for r in answerable if not r["hit3"]],
    }


def main() -> None:
    expected = {
        row["id"]: row["doc"]
        for row in map(json.loads, EXPECTED_PATH.read_text(encoding="utf-8").splitlines())
    }
    sets = {name: load_tickets(path) for name, path in DATASETS.items()}
    pool = open_synced_pool()  # the same search as production: SQL in Postgres
    all_tickets = [t for tickets in sets.values() for t in tickets]
    vectors = dict(
        zip(
            [t.id for t in all_tickets],
            embed([query_text(t.text) for t in all_tickets]),
            strict=True,
        )
    )

    results = {}
    for name, tickets in sets.items():
        rows = []
        for t in tickets:
            with pool.connection() as connection:
                ranked = nearest(connection, vectors[t.id], K, t.language)
            top_docs = [chunk.doc for _, chunk in ranked]
            rows.append(
                {
                    "id": t.id,
                    "language": t.language,
                    "expected": expected[t.id],
                    "top_score": round(ranked[0][0], 3),
                    "top_chunks": [chunk.id for _, chunk in ranked],
                    "hit1": top_docs[0] == expected[t.id],
                    "hit3": expected[t.id] in top_docs,
                }
            )
        summary = summarize(rows)
        results[name] = {"summary": summary, "rows": rows}
        low, high = summary["hit@3_ci"]
        print(
            f"{name}: {summary['answerable']} answerable tickets | hit@1 {summary['hit@1']:.0%} | "
            f"hit@3 {summary['hit@3']:.0%} (95% CI {low:.0%}-{high:.0%})"
        )
        print(
            f"   top score, answerable: min {summary['top_score_answerable'][0]}, mean {summary['top_score_answerable'][1]}"
        )
        print(
            f"   top score, none:       mean {summary['top_score_none'][0]}, max {summary['top_score_none'][1]}"
        )
        print(f"   not in top {K}: {summary['misses'] or 'none'}")
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSaved to {RESULTS_PATH.relative_to(RESULTS_PATH.parent.parent)}")


if __name__ == "__main__":
    main()
