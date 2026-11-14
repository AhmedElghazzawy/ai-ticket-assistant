"""Tests for the ticket history (docs/decisions/0017): every change is recorded with who made it,
in the same statement as the change, and the history cannot be rewritten."""

import psycopg
import pytest
from fakes import fake_result as result

from helpdesk.storage import db as store
from helpdesk.storage.db import Connection, token_hash
from helpdesk.storage.staff import insert_staff
from helpdesk.storage.tickets import (
    list_events,
    mark_handled,
    reassign,
    request_human,
    save_ticket,
)

CODE = "c" * 22


@pytest.fixture
def clerk(db: Connection) -> int:
    """A fees-office staff member's id."""
    return insert_staff(db, "ayse@bilecik.edu.tr", "Ayşe", "staff", "fees", "hash").id


def history(db: Connection, ticket_id: int) -> list[tuple[str, str | None, str | None, str | None]]:
    return [(e.kind, e.staff_name, e.from_office, e.to_office) for e in list_events(db, ticket_id)]


def test_every_ticket_starts_its_history_when_saved(db: Connection) -> None:
    number = save_ticket(db, "q", "tr", result(False))
    assert history(db, number) == [("created", None, None, "fees")]


def test_reassign_and_reply_record_who_did_it(db: Connection, clerk: int) -> None:
    number = save_ticket(db, "q", "tr", result(False))
    reassign(db, number, "it", clerk)
    assert mark_handled(db, number, "answer", clerk)
    assert history(db, number) == [
        ("created", None, None, "fees"),
        ("reassigned", "Ayşe", "fees", "it"),
        ("replied", "Ayşe", None, None),
    ]


def test_a_refused_change_leaves_no_history(db: Connection, clerk: int) -> None:
    number = save_ticket(db, "q", "tr", result(False), access_hash=token_hash(CODE))
    mark_handled(db, number, "first", clerk)
    assert not mark_handled(db, number, "second", clerk)  # someone already replied
    request_human(db, number, CODE)  # handled: stays as it is
    assert [kind for kind, *_ in history(db, number)] == ["created", "replied"]


def test_asking_for_a_person_is_in_the_history(db: Connection) -> None:
    number = save_ticket(db, "q", "tr", result(True), access_hash=token_hash(CODE))
    request_human(db, number, CODE)
    request_human(db, number, CODE)  # a second click changes nothing
    assert history(db, number) == [
        ("created", None, None, "fees"),
        ("human_requested", None, None, None),
    ]


def test_history_cannot_be_rewritten(db: Connection) -> None:
    save_ticket(db, "q", "tr", result(False))
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        db.execute("UPDATE ticket_events SET kind = 'replied'")


def test_tickets_from_before_the_history_get_it_from_their_columns(
    schema: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Live rows from before migration 6: creation, the student's request and the staff reply are
    # rebuilt from the columns they already have (who replied was never stored, so it stays unknown).
    monkeypatch.setattr(store, "MIGRATIONS", {n: s for n, s in store.MIGRATIONS.items() if n <= 5})
    old = store.connect(None, schema)
    row = old.execute(
        "INSERT INTO tickets (created_at, language, text, category, priority, escalate, ai_reason,"
        " office, auto_send, reasons, top_score, draft, covered, sources, status, final_reply,"
        " handled_at, human_requested_at) VALUES (now() - interval '2 hours', 'tr', 'q', 'billing',"
        " 'low', false, 'r', 'fees', true, '[]', 0.7, 'd', true, '[]', 'handled', 'staff reply',"
        " now(), now() - interval '1 hour') RETURNING id"
    ).fetchone()
    assert row is not None
    monkeypatch.undo()
    store.migrate(old)
    rebuilt = history(old, int(row["id"]))
    old.close()
    assert rebuilt == [
        ("created", None, None, "fees"),
        ("human_requested", None, None, None),
        ("replied", None, None, None),
    ]
