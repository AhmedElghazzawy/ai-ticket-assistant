"""Tests for the pipeline eval's answer key: by my labels, should a ticket be auto-sent? No AI calls."""

from helpdesk.domain.tickets import Category, Priority, Ticket
from helpdesk.evals.pipeline import should_auto_send, summarize
from helpdesk.evals.stats import wilson_interval


def ticket(
    category: Category = "billing", priority: Priority = "low", escalate: bool = False
) -> Ticket:
    return Ticket(
        id="x", text="text", language="en", category=category, priority=priority, escalate=escalate
    )


def test_answerable_ticket_should_be_sent() -> None:
    assert should_auto_send(ticket(), "harc_ucretler")


def test_urgent_is_never_sent() -> None:
    # Same rule as domain/decision.py: a person must act today (bug found on tr-p03, Phase 8).
    assert not should_auto_send(ticket(priority="urgent"), "bilisim_hesaplar")


def test_escalation_other_and_no_document_are_not_sent() -> None:
    assert not should_auto_send(ticket(escalate=True), "harc_ucretler")
    assert not should_auto_send(ticket(category="other"), "staj")
    assert not should_auto_send(ticket(), "none")


def result_row(
    tid: str,
    should: bool,
    sent: bool,
    first_help: bool = False,
    general_help: str = "",
    escalate: bool = False,
    cites: bool = True,
    grounded: bool = True,
) -> dict[str, object]:
    return {
        "id": tid,
        "should_auto_send": should,
        "auto_send": sent,
        "first_help": first_help,
        "general_help": general_help,
        "escalate": escalate,
        "cites_expected_doc": cites,
        "sources": ["doc.en#1"],
        "grounded": grounded,
    }


ROWS = [
    result_row("a", should=True, sent=True),
    result_row("b", should=True, sent=False, first_help=True),
    result_row("c", should=False, sent=True),  # unsafe: sent although it needed a human
    result_row("d", should=False, sent=False, first_help=True, escalate=True),  # must never happen
    result_row("e", should=True, sent=False, grounded=False),  # quote not found in the rules
    result_row("f", should=False, sent=False, general_help="try again"),  # only general advice
    result_row("g", should=False, sent=False, general_help="x", escalate=True),  # must never happen
]


def test_pipeline_summary_counts_and_intervals() -> None:
    s = summarize(ROWS)
    assert s["auto_sent"] == 2
    assert s["unsafe_auto_sends"] == ["c"]
    assert s["first_help"] == 2
    assert s["first_help_on_escalated"] == ["d"]
    assert s["ungrounded_citing"] == ["e"]
    assert s["auto_resolution_ci"] == wilson_interval(2, 7)
    assert s["helped_now_ci"] == wilson_interval(4, 7)
    assert s["general_help"] == 2
    assert s["general_help_on_escalated"] == ["g"]
    # A direct answer of any kind: official, first help, or general advice (a, b, c, d, f, g).
    assert s["answered_now"] == "6/7 students got a direct answer"
    assert s["answered_now_ci"] == wilson_interval(6, 7)
