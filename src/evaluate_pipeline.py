"""Phase 4 evaluation: run the whole pipeline and count tickets auto-sent that should not have been.

Run: .venv/bin/python src/evaluate_pipeline.py        (dev tickets)
     .venv/bin/python src/evaluate_pipeline.py test   (the locked test tickets: measure only)
"""

import json
import sys
import time
from pathlib import Path

from pipeline import process_ticket
from retrieval import load_index
from tickets import TEST_PATH, TICKETS_PATH, load_tickets

EXPECTED_PATH = TICKETS_PATH.parent / "expected_docs.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "eval"
WAIT_SECONDS = 5  # pause between tickets (free-tier limits)


def should_auto_send(ticket, expected_doc: str) -> bool:
    """By my labels: no escalation, not 'other', and a document really answers it."""
    return not ticket.escalate and ticket.category != "other" and expected_doc != "none"


def main() -> None:
    on_test = len(sys.argv) > 1 and sys.argv[1] == "test"
    tickets = load_tickets(TEST_PATH if on_test else TICKETS_PATH)
    expected = {r["id"]: r["doc"] for r in map(json.loads, EXPECTED_PATH.read_text(encoding="utf-8").splitlines())}
    index = load_index()
    rows = []
    for number, t in enumerate(tickets, start=1):
        time.sleep(WAIT_SECONDS)
        try:
            r = process_ticket(t.text, t.language, index)
        except Exception as error:  # noqa: BLE001 - skip this ticket, keep the run
            print(f"[{number}/{len(tickets)}] {t.id} ERROR {type(error).__name__}: {error}")
            continue
        cited_docs = {s.split(".")[0] for s in r.answer.sources}
        rows.append({"id": t.id, "text": t.text, "expected_doc": expected[t.id],
                     "should_auto_send": should_auto_send(t, expected[t.id]), "auto_send": r.decision.auto_send,
                     "reasons": r.decision.reasons, "covered": r.answer.covered, "sources": r.answer.sources,
                     "cites_expected_doc": expected[t.id] in cited_docs, "top_score": round(r.hits[0][0], 3),
                     "reply": r.answer.reply})
        print(f"[{number}/{len(tickets)}] {t.id} auto_send={r.decision.auto_send}", flush=True)

    unsafe = [r["id"] for r in rows if r["auto_send"] and not r["should_auto_send"]]
    could = [r for r in rows if r["should_auto_send"]]
    sent = [r for r in rows if r["auto_send"]]
    summary = {
        "tickets": len(rows),
        "auto_sent": len(sent),
        "unsafe_auto_sends": unsafe,
        "helpful": f"{sum(r['auto_send'] for r in could)}/{len(could)} answerable tickets were auto-sent",
        "wrong_document_cited": [r["id"] for r in sent if not r["cites_expected_doc"]],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    path = RESULTS_DIR / f"pipeline_results_{'test' if on_test else 'dev'}.json"
    path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved to {path.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
