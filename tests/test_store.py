"""Tests for the ticket store, on a real Postgres (each test gets a fresh schema: conftest.py)."""

import os
import subprocess
import sys
from datetime import timedelta

import store
from answer import Answer
from classifier import Classification
from decision import Decision, SimpleReason, WeakMatch
from knowledge_base import Chunk
from pipeline import TicketResult
from store import Connection, get_ticket, list_tickets, mark_handled, reassign, save_ticket
from tickets import Priority

CHUNK = Chunk(
    id="harc_ucretler.tr#5",
    doc="harc_ucretler",
    language="tr",
    title="Katkı Payı ve İadeler",
    source="Öğrenci İşleri SSS",
    url="https://bilecik.edu.tr/ogrenciisleri/Icerik/HARc_isLEMLERi",
    text="Kayıt sildirince iade\nGeri ödenmez.",
)


def result(auto_send: bool, priority: Priority = "low") -> TicketResult:
    """A hand-made pipeline result: a billing ticket that cites one retrieved rule."""
    return TicketResult(
        classification=Classification(
            reason="the model's explanation", category="billing", priority=priority, escalate=False
        ),
        hits=[(0.6497, CHUNK)],
        answer=Answer(evidence="", covered=True, reply="a draft", sources=[CHUNK.id]),
        decision=Decision(
            auto_send=auto_send,
            reasons=[]
            if auto_send
            else [SimpleReason(code="escalation"), WeakMatch(score=0.6497, min=0.65)],
        ),
    )


def test_save_returns_increasing_ticket_numbers(db: Connection) -> None:
    first = save_ticket(db, "q1", "tr", result(False))
    second = save_ticket(db, "q2", "tr", result(False))
    assert second == first + 1


def test_everything_staff_need_is_saved_and_read_back(db: Connection) -> None:
    ticket = get_ticket(db, save_ticket(db, "Harç iade edilir mi?", "tr", result(False)))
    assert ticket is not None
    assert ticket.office == "fees"  # an office ID, not a name
    assert ticket.ai_reason == "the model's explanation"
    assert ticket.reasons == [SimpleReason(code="escalation"), WeakMatch(score=0.6497, min=0.65)]
    assert ticket.top_score == 0.6497 and ticket.covered and not ticket.demo
    assert ticket.created_at.utcoffset() == timedelta(0)  # UTC: every browser shows its local time
    [source] = ticket.sources
    assert (source.section, source.url) == ("Kayıt sildirince iade", CHUNK.url)


def test_unknown_ticket_number_gives_none(db: Connection) -> None:
    assert get_ticket(db, 999) is None


def test_forwarded_tickets_are_open_and_auto_sent_are_not(db: Connection) -> None:
    save_ticket(db, "forwarded", "tr", result(False))
    save_ticket(db, "answered", "tr", result(True))
    assert [t.text for t in list_tickets(db, "open")] == ["forwarded"]
    assert [t.text for t in list_tickets(db, "auto_sent")] == ["answered"]


def test_queue_shows_urgent_first(db: Connection) -> None:
    save_ticket(db, "low one", "tr", result(False, "low"))
    save_ticket(db, "urgent one", "tr", result(False, "urgent"))
    assert list_tickets(db, "open")[0].text == "urgent one"


def test_mark_handled_moves_ticket_out_of_the_queue(db: Connection) -> None:
    number = save_ticket(db, "q", "tr", result(False))
    assert mark_handled(db, number, "final answer from staff")
    assert list_tickets(db, "open") == []
    handled = list_tickets(db, "handled")[0]
    assert handled.final_reply == "final answer from staff" and handled.handled_at


def test_only_one_reply_can_close_a_ticket(db: Connection) -> None:
    # One atomic UPDATE ... WHERE status = 'open': if two staff members send at the same
    # moment, exactly one wins and the other is told (no lost reply, no double answer).
    number = save_ticket(db, "q", "tr", result(False))
    assert mark_handled(db, number, "first") is True
    assert mark_handled(db, number, "second") is False
    ticket = get_ticket(db, number)
    assert ticket is not None and ticket.final_reply == "first"


def test_reassign_changes_the_office(db: Connection) -> None:
    number = save_ticket(db, "q", "tr", result(False))
    reassign(db, number, "student_affairs")
    ticket = get_ticket(db, number)
    assert ticket is not None and ticket.office == "student_affairs"


def test_sql_injection_text_is_stored_as_plain_text(db: Connection) -> None:
    attack = "'; DROP TABLE tickets; --"
    save_ticket(db, attack, "tr", result(False))
    assert list_tickets(db, "open")[0].text == attack  # the table still exists and holds the text


def test_migrations_are_recorded_and_running_them_again_changes_nothing(db: Connection) -> None:
    versions = [r["version"] for r in db.execute("SELECT version FROM schema_migrations")]
    assert versions == sorted(store.MIGRATIONS)
    save_ticket(db, "kept", "tr", result(False))
    store.migrate(db)  # e.g. a second app instance starting
    assert [r["version"] for r in db.execute("SELECT version FROM schema_migrations")] == versions
    assert [t.text for t in list_tickets(db, "open")] == ["kept"]


def test_database_address_comes_from_the_environment() -> None:
    # Production (Neon) sets DATABASE_URL as a secret; nothing is hard-coded.
    env = {**os.environ, "DATABASE_URL": "postgresql://u:p@neon.example/db", "PYTHONPATH": "src"}
    code = "import store; print(store.DATABASE_URL)"
    result_ = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert result_.stdout.strip() == "postgresql://u:p@neon.example/db"


def test_inside_a_priority_the_ticket_that_waited_longest_comes_first(db: Connection) -> None:
    store.reset_demo_tickets(db)  # demo tickets have back-dated arrival times
    queue = list_tickets(db, "open", demo=True)
    for priority in ("urgent", "high", "medium", "low"):
        times = [t.created_at for t in queue if t.priority == priority]
        assert times == sorted(times), priority  # oldest first, by real arrival time
