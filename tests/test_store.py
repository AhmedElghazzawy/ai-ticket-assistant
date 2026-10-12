"""Tests for the ticket store. Each test uses its own temporary database (pytest's tmp_path)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

import store
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


def test_a_version_2_database_is_upgraded_and_keeps_its_tickets(tmp_path: Path) -> None:
    path = tmp_path / "v2.db"
    with sqlite3.connect(path) as old:  # exactly what version 2 created, with one ticket in it
        old.executescript(store.MIGRATIONS[2] + "PRAGMA user_version = 2;")
        old.execute(
            "INSERT INTO tickets (created_at, language, text, category, priority, escalate,"
            " ai_reason, office, auto_send, reasons, top_score, draft, covered, sources, status)"
            " VALUES ('2026-10-11T10:00:00+00:00', 'tr', 'an old ticket', 'billing', 'low', 0,"
            " 'r', 'fees', 0, '[]', 0.7, 'd', 1, '[]', 'open')"
        )
    upgraded = connect(path)
    assert upgraded.execute("PRAGMA user_version").fetchone()[0] == store.SCHEMA_VERSION
    assert [t.text for t in list_tickets(upgraded, "open")] == ["an old ticket"]  # data kept
    assert upgraded.execute("SELECT count(*) FROM staff").fetchone()[0] == 0  # new table exists


def test_version_4_separates_demo_tickets_and_demo_staff(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    assert db.execute("PRAGMA user_version").fetchone()[0] == 4
    ticket = get_ticket(db, save_ticket(db, "a real visitor", "tr", result(False)))
    assert ticket is not None and ticket.demo is False  # real tickets are never demo tickets
    columns = {row[1] for row in db.execute("PRAGMA table_info(staff)")}
    assert "demo" in columns


def test_inside_a_priority_the_ticket_that_waited_longest_comes_first(tmp_path: Path) -> None:
    db = connect(tmp_path / "test.db")
    store.reset_demo_tickets(db)  # demo tickets have back-dated arrival times
    queue = list_tickets(db, "open", demo=True)
    for priority in ("urgent", "high", "medium", "low"):
        times = [t.created_at for t in queue if t.priority == priority]
        assert times == sorted(times), priority  # oldest first, by real arrival time
