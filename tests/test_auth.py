"""Staff accounts and sessions: the rules that keep student data safe."""

import hashlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from helpdesk import auth
from helpdesk.storage import db as store
from helpdesk.storage.db import Connection

GOOD_PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def ayse(db: Connection) -> None:
    """One staff member in the fresh test schema (conftest.py gives every test its own)."""
    auth.create_staff(db, "ayse@bilecik.edu.tr", "Ayşe", "staff", "it", GOOD_PASSWORD)


def test_password_is_stored_as_an_argon2id_hash(db: Connection) -> None:
    row = db.execute("SELECT password_hash FROM staff").fetchone()
    assert row is not None
    stored = row["password_hash"]
    assert stored.startswith("$argon2id$") and GOOD_PASSWORD not in stored


def test_right_password_logs_in_and_email_case_does_not_matter(db: Connection) -> None:
    staff = auth.authenticate(db, "AYSE@bilecik.edu.tr", GOOD_PASSWORD, ip="1.2.3.4")
    assert staff is not None and staff.name == "Ayşe" and staff.office == "it"


def test_wrong_password_and_unknown_email_both_fail(db: Connection) -> None:
    assert auth.authenticate(db, "ayse@bilecik.edu.tr", "wrong password!", ip="1.2.3.4") is None
    assert auth.authenticate(db, "nobody@bilecik.edu.tr", GOOD_PASSWORD, ip="1.2.3.4") is None


def test_too_many_failures_block_even_the_right_password(db: Connection) -> None:
    for _ in range(auth.MAX_FAILURES_PER_EMAIL):
        auth.authenticate(db, "ayse@bilecik.edu.tr", "guess guess guess", ip="1.2.3.4")
    with pytest.raises(auth.TooManyAttempts):
        auth.authenticate(db, "ayse@bilecik.edu.tr", GOOD_PASSWORD, ip="5.6.7.8")


def test_staff_need_an_office_admins_do_not(db: Connection) -> None:
    with pytest.raises(ValueError, match="office"):
        auth.create_staff(db, "a@x.tr", "A", "staff", None, GOOD_PASSWORD)
    with pytest.raises(ValueError, match="office"):
        auth.create_staff(db, "b@x.tr", "B", "admin", "it", GOOD_PASSWORD)
    auth.create_staff(db, "c@x.tr", "C", "admin", None, GOOD_PASSWORD)


def test_short_passwords_and_duplicate_emails_are_refused(db: Connection) -> None:
    with pytest.raises(ValueError, match="at least"):
        auth.create_staff(db, "d@x.tr", "D", "staff", "it", "short")
    with pytest.raises(ValueError, match="already"):
        auth.create_staff(db, "AYSE@bilecik.edu.tr", "Copy", "staff", "it", GOOD_PASSWORD)


def ayse_id(db: Connection) -> int:
    row = db.execute("SELECT id FROM staff WHERE email = 'ayse@bilecik.edu.tr'").fetchone()
    assert row is not None
    return int(row["id"])


def test_session_token_is_stored_only_as_a_hash(db: Connection) -> None:
    token = auth.create_session(db, staff_id=ayse_id(db))
    row = db.execute("SELECT token_hash FROM sessions").fetchone()
    assert row is not None
    stored = row["token_hash"]
    assert stored == hashlib.sha256(token.encode()).hexdigest() and token not in stored
    staff = auth.staff_for_session(db, token)
    assert staff is not None and staff.email == "ayse@bilecik.edu.tr"


def test_expired_or_ended_sessions_do_not_work(db: Connection) -> None:
    token = auth.create_session(db, staff_id=ayse_id(db))
    past = datetime.now(UTC) - timedelta(minutes=1)
    db.execute("UPDATE sessions SET expires_at = %s", (past,))
    assert auth.staff_for_session(db, token) is None
    token = auth.create_session(db, staff_id=ayse_id(db))
    auth.end_session(db, token)
    assert auth.staff_for_session(db, token) is None
    assert auth.staff_for_session(db, "a made-up token") is None


def test_add_staff_tool_creates_an_account(
    db: Connection, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import add_staff

    schema = db.execute("SELECT current_schema() AS s").fetchone()
    assert schema is not None
    # the tool gets its own connection to this test's schema (it closes it when done), never real data
    monkeypatch.setattr(
        add_staff, "connect", lambda *args: store.connect(store.database_url(), schema["s"])
    )
    monkeypatch.setattr(add_staff, "getpass", lambda prompt: GOOD_PASSWORD)  # the hidden prompt
    monkeypatch.setattr(
        sys, "argv", ["add_staff", "mehmet@bilecik.edu.tr", "Mehmet", "--office", "sks"]
    )
    add_staff.main()
    assert "Created mehmet@bilecik.edu.tr (sks)" in capsys.readouterr().out
    staff = auth.authenticate(db, "mehmet@bilecik.edu.tr", GOOD_PASSWORD, "1.2.3.4")
    assert staff is not None and staff.office == "sks"
