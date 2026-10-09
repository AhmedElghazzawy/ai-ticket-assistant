"""Score the classifier against my labels and save the run to eval/.

Run: .venv/bin/python src/evaluate.py high        (dev tickets, thinking level high)
     .venv/bin/python src/evaluate.py high test   (the LOCKED test tickets: measure only, never tune on them)
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from google.genai import errors, types

from classifier import THINKING_LEVEL, classify
from llm import MODEL
from tickets import TEST_PATH, TICKETS_PATH, Ticket, load_tickets

RUNS = 2  # each ticket is classified twice, to measure consistency
WAIT_SECONDS = 5  # pause between calls to stay under the free-tier requests-per-minute limit

Predictions = dict[str, dict]  # ticket id -> {"reason", "category", "priority", "escalate"}


def predict_all(tickets: list[Ticket], thinking_level: types.ThinkingLevel) -> list[Predictions]:
    """Classify every ticket RUNS times. Stops early (keeping what it has) if the quota is used up."""
    runs: list[Predictions] = []
    for run_number in range(1, RUNS + 1):
        predictions: Predictions = {}
        runs.append(predictions)
        for number, ticket in enumerate(tickets, start=1):
            time.sleep(WAIT_SECONDS)
            try:
                predictions[ticket.id] = classify(ticket.text, thinking_level).model_dump()
            except errors.ClientError as error:
                if error.code == 429:
                    print(f"Quota used up (429) in run {run_number}. Stopping; partial results are kept.")
                    return runs
                print(f"run {run_number} [{number}/{len(tickets)}] {ticket.id} ERROR {error.code}: {error.message}")
                continue
            except Exception as error:  # noqa: BLE001 - e.g. a timeout: skip this ticket instead of losing the whole run
                print(f"run {run_number} [{number}/{len(tickets)}] {ticket.id} ERROR {type(error).__name__}: {error}")
                continue
            print(f"run {run_number} [{number}/{len(tickets)}] {ticket.id}", flush=True)
    return runs


FIELDS = ("category", "priority", "escalate")
PRIORITY_ORDER = ["low", "medium", "high", "urgent"]


def score(tickets: list[Ticket], predictions: Predictions) -> dict:
    """Compare one run with my labels: accuracy per label, all three, priority within one level, escalation errors."""
    done = [t for t in tickets if t.id in predictions]
    if not done:
        return {"n": 0}
    result: dict = {"n": len(done)}
    for field in FIELDS:
        result[field] = sum(predictions[t.id][field] == getattr(t, field) for t in done) / len(done)
    result["all_three"] = sum(all(predictions[t.id][f] == getattr(t, f) for f in FIELDS) for t in done) / len(done)
    result["priority_within_one"] = sum(
        abs(PRIORITY_ORDER.index(predictions[t.id]["priority"]) - PRIORITY_ORDER.index(t.priority)) <= 1
        for t in done
    ) / len(done)
    # The most dangerous error: the ticket needed a human, but the model did not escalate.
    result["missed_escalations"] = [t.id for t in done if t.escalate and not predictions[t.id]["escalate"]]
    # The safe error: a human gets a ticket that did not need one.
    result["over_escalations"] = [t.id for t in done if not t.escalate and predictions[t.id]["escalate"]]
    return result


def consistency(first: Predictions, second: Predictions) -> dict:
    """How often the model gives the same label to the same ticket in two runs."""
    both = [tid for tid in first if tid in second]
    if not both:
        return {"n": 0}
    result: dict = {"n": len(both)}
    for field in FIELDS:
        result[field] = sum(first[tid][field] == second[tid][field] for tid in both) / len(both)
    result["changed"] = [tid for tid in both if any(first[tid][f] != second[tid][f] for f in FIELDS)]
    return result


RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval"


def print_report(results: dict) -> None:
    """Show the main numbers in the terminal."""
    print(f"\nModel {results['model']}, thinking {results['thinking_level']}, runs completed: {results['runs']}")
    print(f"{'':22}{'all':>7}{'tr':>7}{'en':>7}")
    for key in ("category", "priority", "escalate", "all_three", "priority_within_one"):
        row = [results[s].get(key) for s in ("score_run1", "score_run1_tr", "score_run1_en")]
        print(f"{key:22}" + "".join(f"{v:>7.1%}" if v is not None else f"{'-':>7}" for v in row))
    print("missed escalations:", results["score_run1"].get("missed_escalations") or "none")
    print("over-escalations:  ", results["score_run1"].get("over_escalations") or "none")
    if results["consistency"]:
        c = results["consistency"]
        print(f"consistency (run 1 vs run 2, {c['n']} tickets): category {c['category']:.0%}, "
              f"priority {c['priority']:.0%}, escalate {c['escalate']:.0%}; changed: {c['changed'] or 'none'}")


def print_mistakes(tickets: list[Ticket], predictions: Predictions) -> None:
    """Every ticket where run 1 disagrees with my labels, with the model's reason."""
    print("\nMistakes in run 1:")
    for t in tickets:
        p = predictions.get(t.id)
        wrong = [f for f in FIELDS if p and p[f] != getattr(t, f)]
        if wrong:
            diffs = ", ".join(f"{f}: model={p[f]} mine={getattr(t, f)}" for f in wrong)
            print(f"- {t.id} | {diffs}\n    {t.text}\n    reason: {p['reason']}")


def main() -> None:
    level = types.ThinkingLevel[sys.argv[1].upper()] if len(sys.argv) > 1 else THINKING_LEVEL
    on_test = len(sys.argv) > 2 and sys.argv[2] == "test"
    tickets = load_tickets(TEST_PATH if on_test else TICKETS_PATH)
    runs = predict_all(tickets, level)
    by_language = {lang: [t for t in tickets if t.language == lang] for lang in ("tr", "en")}
    results = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "thinking_level": level.value,
        "dataset": "test" if on_test else "dev",
        "runs": len(runs),
        "score_run1": score(tickets, runs[0]),
        "score_run1_tr": score(by_language["tr"], runs[0]),
        "score_run1_en": score(by_language["en"], runs[0]),
        "score_run2": score(tickets, runs[1]) if len(runs) > 1 else None,
        "consistency": consistency(runs[0], runs[1]) if len(runs) > 1 else None,
        "predictions": runs,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    suffix = "_test" if on_test else ""
    path = RESULTS_DIR / f"results_{level.value.lower()}{suffix}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print_report(results)
    print_mistakes(tickets, runs[0])
    print(f"\nSaved to {path.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
