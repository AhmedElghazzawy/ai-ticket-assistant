"""Tests for the ticket store. Each test uses its own temporary database (pytest's tmp_path)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from answer import Answer
from classifier import Classification
from decision import Decision, SimpleReason, WeakMatch
from knowledge_base import Chunk
from pipeline import TicketResult
from store import connect, get_ticket, list_tickets, mark_handled, reassign, save_ticket
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


def test_save_returns_increasing_ticket_numbers(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    first = save_ticket(db, "q1", "tr", result(False))
    second = save_ticket(db, "q2", "tr", result(False))
    assert second == first + 1


def test_everything_staff_need_is_saved_and_read_back(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    ticket = get_ticket(db, save_ticket(db, "Harç iade edilir mi?", "tr", result(False)))
    assert ticket is not None
    assert ticket.office == "fees"  # an office ID, not a name
    assert ticket.ai_reason == "the model's explanation"
    assert ticket.reasons == [SimpleReason(code="escalation"), WeakMatch(score=0.6497, min=0.65)]
    assert ticket.top_score == 0.6497 and ticket.covered
    assert ticket.created_at.endswith("+00:00")  # UTC, so every browser shows its own local time
    [source] = ticket.sources
    assert (source.section, source.url) == ("Kayıt sildirince iade", CHUNK.url)


def test_unknown_ticket_number_gives_none(tmp_path: Path) -> None:
    assert get_ticket(connect(tmp_path / "test.db"), 999) is None


def test_forwarded_tickets_are_open_and_auto_sent_are_not(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    save_ticket(db, "forwarded", "tr", result(False))
    save_ticket(db, "answered", "tr", result(True))
    assert [t.text for t in list_tickets(db, "open")] == ["forwarded"]
    assert [t.text for t in list_tickets(db, "auto_sent")] == ["answered"]


def test_queue_shows_urgent_first(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    save_ticket(db, "low one", "tr", result(False, "low"))
    save_ticket(db, "urgent one", "tr", result(False, "urgent"))
    assert list_tickets(db, "open")[0].text == "urgent one"


def test_mark_handled_moves_ticket_out_of_the_queue(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    number = save_ticket(db, "q", "tr", result(False))
    mark_handled(db, number, "final answer from staff")
    assert list_tickets(db, "open") == []
    handled = list_tickets(db, "handled")[0]
    assert handled.final_reply == "final answer from staff" and handled.handled_at


def test_reassign_changes_the_office(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    number = save_ticket(db, "q", "tr", result(False))
    reassign(db, number, "student_affairs")
    ticket = get_ticket(db, number)
    assert ticket is not None and ticket.office == "student_affairs"


def test_sql_injection_text_is_stored_as_plain_text(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    attack = "'; DROP TABLE tickets; --"
    save_ticket(db, attack, "tr", result(False))
    assert list_tickets(db, "open")[0].text == attack  # the table still exists and holds the text


def test_old_database_is_refused_with_a_clear_message(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as old:  # a version-1 database: no user_version, old columns
        old.execute("CREATE TABLE tickets (id INTEGER PRIMARY KEY, text TEXT)")
    with pytest.raises(RuntimeError, match="delete the file"):
        connect(path)


def test_database_path_can_be_set_by_environment(tmp_path: Path) -> None:
    # Docker keeps the database in a volume: HELPDESK_DB points there.
    env = {**os.environ, "HELPDESK_DB": str(tmp_path / "volume.db"), "PYTHONPATH": "src"}
    code = "import store; print(store.DB_PATH)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert result.stdout.strip() == str(tmp_path / "volume.db")
