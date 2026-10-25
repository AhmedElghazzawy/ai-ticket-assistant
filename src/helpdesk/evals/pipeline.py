"""Phase 4 evaluation: run the whole pipeline and count tickets auto-sent that should not have been.

Run: make eval-pipeline              (dev tickets)
     make eval-pipeline SET=test     (the locked test tickets: measure only)
     make eval-pipeline SET=phase8   (the locked Phase 8 tickets: measure only)
"""

import json
import sys
import time
from typing import Any

from helpdesk.ai.gemini import GeminiProvider
from helpdesk.core.paths import EVAL_DIR
from helpdesk.domain.decision import show_first_help
from helpdesk.domain.grounding import is_grounded
from helpdesk.domain.tickets import DATASETS, TICKETS_PATH, Ticket, load_tickets
from helpdesk.evals.stats import wilson_interval
from helpdesk.pipeline import process_ticket
from helpdesk.retrieval.search import open_synced_pool

EXPECTED_PATH = TICKETS_PATH.parent / "expected_docs.jsonl"
RESULTS_DIR = EVAL_DIR
WAIT_SECONDS = 5  # pause between tickets (free-tier limits)


def should_auto_send(ticket: Ticket, expected_doc: str) -> bool:
    """By my labels: no escalation, not 'other', not urgent, and a document really answers it."""
    return (
        not ticket.escalate
        and ticket.category != "other"
        and ticket.priority != "urgent"  # same rule as domain/decision.py
        and expected_doc != "none"
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Safety counts (must stay empty) and helpfulness rates with their 95% intervals."""
    could = [r for r in rows if r["should_auto_send"]]
    sent = [r for r in rows if r["auto_send"]]
    first_help = [r for r in rows if r["first_help"]]
    helped = len(sent) + len(first_help)
    return {
        "tickets": len(rows),
        "auto_sent": len(sent),
        "unsafe_auto_sends": [r["id"] for r in sent if not r["should_auto_send"]],
        "helpful": f"{sum(r['auto_send'] for r in could)}/{len(could)} answerable tickets were auto-sent",
        "wrong_document_cited": [r["id"] for r in sent if not r["cites_expected_doc"]],
        "auto_resolution_ci": wilson_interval(len(sent), len(rows)),
        "first_help": len(first_help),
        "helped_now": f"{helped}/{len(rows)} students got an answer or first help",
        "helped_now_ci": wilson_interval(helped, len(rows)),
        # Must stay empty: AI text shown to a student whose ticket (by my labels) needed a human.
        "first_help_on_escalated": [r["id"] for r in first_help if r["escalate"]],
        # Answers that cite a rule but whose quoted evidence is not found in the retrieved rules.
        "ungrounded_citing": [r["id"] for r in rows if r["sources"] and not r["grounded"]],
    }


def main() -> None:
    dataset = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if dataset not in DATASETS:
        sys.exit(f"Unknown dataset {dataset!r}; choose one of {list(DATASETS)}")
    tickets = load_tickets(DATASETS[dataset])
    expected = {
        r["id"]: r["doc"]
        for r in map(json.loads, EXPECTED_PATH.read_text(encoding="utf-8").splitlines())
    }
    pool = open_synced_pool()
    llm = GeminiProvider()
    rows = []
    for number, t in enumerate(tickets, start=1):
        time.sleep(WAIT_SECONDS)
        try:
            r = process_ticket(t.text, t.language, pool.connection, llm)
        except Exception as error:  # noqa: BLE001 - skip this ticket, keep the run
            print(f"[{number}/{len(tickets)}] {t.id} ERROR {type(error).__name__}: {error}")
            continue
        cited_docs = {s.split(".")[0] for s in r.answer.sources}
        rows.append(
            {
                "id": t.id,
                "text": t.text,
                "expected_doc": expected[t.id],
                "should_auto_send": should_auto_send(t, expected[t.id]),
                "auto_send": r.decision.auto_send,
                "first_help": show_first_help(r.decision),
                "escalate": t.escalate,
                "reasons": [reason.model_dump() for reason in r.decision.reasons],
                "covered": r.answer.covered,
                "sources": r.answer.sources,
                "cites_expected_doc": expected[t.id] in cited_docs,
                "top_score": round(r.hits[0][0], 3),
                "reply": r.answer.reply,
                "evidence": r.answer.evidence,
                "grounded": is_grounded(r.answer.evidence, [c.text for _, c in r.hits]),
            }
        )
        print(f"[{number}/{len(tickets)}] {t.id} auto_send={r.decision.auto_send}", flush=True)

    summary = summarize(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    path = RESULTS_DIR / f"pipeline_results_{dataset}.json"
    path.write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"Saved to {path.relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
