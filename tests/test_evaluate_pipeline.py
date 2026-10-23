"""Tests for the pipeline eval's answer key: by my labels, should a ticket be auto-sent? No AI calls."""

from evaluate_pipeline import should_auto_send
from tickets import Category, Priority, Ticket


def ticket(
    category: Category = "billing", priority: Priority = "low", escalate: bool = False
) -> Ticket:
    return Ticket(
        id="x", text="text", language="en", category=category, priority=priority, escalate=escalate
    )


def test_answerable_ticket_should_be_sent() -> None:
    assert should_auto_send(ticket(), "harc_ucretler")


def test_urgent_is_never_sent() -> None:
    # Same rule as src/decision.py: a person must act today (bug found on tr-p03, Phase 8).
    assert not should_auto_send(ticket(priority="urgent"), "bilisim_hesaplar")


def test_escalation_other_and_no_document_are_not_sent() -> None:
    assert not should_auto_send(ticket(escalate=True), "harc_ucretler")
    assert not should_auto_send(ticket(category="other"), "staj")
    assert not should_auto_send(ticket(), "none")
