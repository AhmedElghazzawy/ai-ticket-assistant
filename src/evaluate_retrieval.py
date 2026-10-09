"""Measure retrieval: is the right document in the top 3 for each ticket?

Run: .venv/bin/python src/evaluate_retrieval.py
"""

import json
from pathlib import Path
from statistics import mean

from retrieval import embed, load_index, query_text, similarity
from tickets import TEST_PATH, TICKETS_PATH, load_tickets

EXPECTED_PATH = TICKETS_PATH.parent / "expected_docs.jsonl"
RESULTS_PATH = Path(__file__).resolve().parent.parent / "eval" / "retrieval_results.json"
K = 3


def ranked_docs(query_vector: list[float], index: list, language: str) -> list[tuple[float, str, str]]:
    """All chunks in the ticket's language, best first, as (score, doc, chunk id)."""
    scored = [(similarity(query_vector, v), c.doc, c.id) for c, v in index if c.language == language]
    return sorted(scored, reverse=True)


def main() -> None:
    expected = {row["id"]: row["doc"] for row in map(json.loads, EXPECTED_PATH.read_text(encoding="utf-8").splitlines())}
    sets = {"dev": load_tickets(TICKETS_PATH), "test": load_tickets(TEST_PATH)}
    index = load_index()
    all_tickets = sets["dev"] + sets["test"]
    vectors = dict(zip([t.id for t in all_tickets], embed([query_text(t.text) for t in all_tickets])))

    results = {}
    for name, tickets in sets.items():
        rows = []
        for t in tickets:
            ranked = ranked_docs(vectors[t.id], index, t.language)
            top_docs = [doc for _, doc, _ in ranked[:K]]
            rows.append({"id": t.id, "language": t.language, "expected": expected[t.id], "top_score": round(ranked[0][0], 3),
                         "top_chunks": [cid for _, _, cid in ranked[:K]],
                         "hit1": top_docs[0] == expected[t.id], "hit3": expected[t.id] in top_docs})
        answerable = [r for r in rows if r["expected"] != "none"]
        unanswerable = [r for r in rows if r["expected"] == "none"]
        summary = {
            "answerable": len(answerable),
            "hit@1": mean(r["hit1"] for r in answerable),
            "hit@3": mean(r["hit3"] for r in answerable),
            "top_score_answerable": [round(min(r["top_score"] for r in answerable), 3), round(mean(r["top_score"] for r in answerable), 3)],
            "top_score_none": [round(mean(r["top_score"] for r in unanswerable), 3), round(max(r["top_score"] for r in unanswerable), 3)],
            "misses": [r["id"] for r in answerable if not r["hit3"]],
        }
        results[name] = {"summary": summary, "rows": rows}
        print(f"{name}: {summary['answerable']} answerable tickets | hit@1 {summary['hit@1']:.0%} | hit@3 {summary['hit@3']:.0%}")
        print(f"   top score, answerable: min {summary['top_score_answerable'][0]}, mean {summary['top_score_answerable'][1]}")
        print(f"   top score, none:       mean {summary['top_score_none'][0]}, max {summary['top_score_none'][1]}")
        print(f"   not in top {K}: {summary['misses'] or 'none'}")
    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSaved to {RESULTS_PATH.relative_to(RESULTS_PATH.parent.parent)}")


if __name__ == "__main__":
    main()
