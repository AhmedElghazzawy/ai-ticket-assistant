"""Tests for the ticket store. Each test uses its own temporary database (pytest's tmp_path)."""

from answer import Answer
from classifier import Classification
from decision import Decision
from pipeline import TicketResult
from store import connect, list_tickets, mark_handled, save_ticket


def result(auto_send: bool, priority: str = "low") -> TicketResult:
    """A hand-made pipeline result."""
    return TicketResult(
        classification=Classification(reason="test", category="billing", priority=priority, escalate=False),
        hits=[],
        answer=Answer(evidence="", covered=False, reply="a draft", sources=[]),
        decision=Decision(auto_send=auto_send, reasons=[] if auto_send else ["test reason"]),
    )


def test_save_returns_increasing_ticket_numbers(tmp_path):
    db = connect(tmp_path / "test.db")
    first = save_ticket(db, "q1", "tr", result(False), "Office")
    second = save_ticket(db, "q2", "tr", result(False), "Office")
    assert second == first + 1


def test_forwarded_tickets_are_open_and_auto_sent_are_not(tmp_path):
    db = connect(tmp_path / "test.db")
    save_ticket(db, "forwarded", "tr", result(False), "Office")
    save_ticket(db, "answered", "tr", result(True), "Office")
    assert [row["text"] for row in list_tickets(db, "open")] == ["forwarded"]
    assert [row["text"] for row in list_tickets(db, "auto_sent")] == ["answered"]


def test_queue_shows_urgent_first(tmp_path):
    db = connect(tmp_path / "test.db")
    save_ticket(db, "low one", "tr", result(False, "low"), "Office")
    save_ticket(db, "urgent one", "tr", result(False, "urgent"), "Office")
    assert list_tickets(db, "open")[0]["text"] == "urgent one"


def test_mark_handled_moves_ticket_out_of_the_queue(tmp_path):
    db = connect(tmp_path / "test.db")
    number = save_ticket(db, "q", "tr", result(False), "Office")
    mark_handled(db, number, "final answer from staff")
    assert list_tickets(db, "open") == []
    handled = list_tickets(db, "handled")[0]
    assert handled["final_reply"] == "final answer from staff" and handled["handled_at"]


def test_sql_injection_text_is_stored_as_plain_text(tmp_path):
    db = connect(tmp_path / "test.db")
    attack = "'; DROP TABLE tickets; --"
    save_ticket(db, attack, "tr", result(False), "Office")
    assert list_tickets(db, "open")[0]["text"] == attack  # the table still exists and holds the text
