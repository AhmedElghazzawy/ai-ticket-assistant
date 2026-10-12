"""Build data/demo_tickets.json: the sample queue of the staff console's demo mode.

Everything is REAL output of this project, nothing invented: the dev tickets (data/tickets),
the classifier's labels and its own explanation (eval/results_high.json, run 1), and the
pipeline's drafts, sources and retrieval checks (eval/pipeline_results_dev.json).
Run: uv run python tools/make_demo_tickets.py
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from decision import MIN_SCORE, OFFICE_OF  # noqa: E402  (src/ must be on the path first)
from knowledge_base import load_chunks  # noqa: E402
from tickets import TICKETS_PATH, load_tickets  # noqa: E402

OUTPUT = ROOT / "data" / "demo_tickets.json"
QUOTA = {"urgent": 3, "high": 4, "medium": 5, "low": 4}  # a realistic queue, not all urgent
MAX_PER_CATEGORY = 3


def reasons(row: dict[str, Any], labels: dict[str, Any]) -> list[dict[str, Any]]:
    """Today's reason codes: labels from the classifier, retrieval checks from the pipeline run
    (that run predates the 'urgent' rule, so it is added from the label)."""
    found: list[dict[str, Any]] = []
    if labels["category"] == "other":
        found.append({"code": "category_other"})
    if labels["escalate"]:
        found.append({"code": "escalation"})
    if labels["priority"] == "urgent":
        found.append({"code": "urgent"})
    for sentence in row["reasons"]:
        if sentence.startswith("weak document match"):
            found.append({"code": "weak_match", "score": row["top_score"], "min": MIN_SCORE})
        elif sentence.startswith("the documents do not answer"):
            found.append({"code": "not_covered"})
        elif sentence.startswith("the reply does not cite"):
            found.append({"code": "no_citation"})
    return found


def main() -> None:
    tickets = {t.id: t for t in load_tickets(TICKETS_PATH)}
    labels = json.loads((ROOT / "eval" / "results_high.json").read_text(encoding="utf-8"))
    predictions = labels["predictions"][0]
    rows = json.loads((ROOT / "eval" / "pipeline_results_dev.json").read_text(encoding="utf-8"))
    chunks = {c.id: c for c in load_chunks()}

    quota, per_category = dict(QUOTA), Counter[str]()
    chosen: list[dict[str, Any]] = []
    for row in sorted(
        rows["rows"], key=lambda r: (not r["sources"], r["id"])
    ):  # with sources first
        label = predictions[row["id"]]
        found = reasons(row, label)
        if not found or quota[label["priority"]] == 0:  # no reason: it was auto-sent, not queued
            continue
        if per_category[label["category"]] >= MAX_PER_CATEGORY:
            continue
        quota[label["priority"]] -= 1
        per_category[label["category"]] += 1
        ticket = tickets[row["id"]]
        chosen.append(
            {
                "age_minutes": 4 + 23 * len(chosen),  # arrival time, relative to the demo login
                "language": ticket.language,
                "text": ticket.text,
                "category": label["category"],
                "priority": label["priority"],
                "escalate": label["escalate"],
                "ai_reason": label["reason"],
                "office": OFFICE_OF[label["category"]],
                "reasons": found,
                "top_score": row["top_score"],
                "draft": row["reply"],
                "covered": row["covered"],
                "sources": [
                    {
                        "id": i,
                        "title": chunks[i].title,
                        "section": chunks[i].section,
                        "url": chunks[i].url,
                    }
                    for i in row["sources"]
                    if i in chunks
                ],
            }
        )
    OUTPUT.write_text(json.dumps(chosen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    priorities = Counter(t["priority"] for t in chosen)
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {len(chosen)} tickets {dict(priorities)}")


if __name__ == "__main__":
    main()
