"""Staff accounts, passwords and login sessions.

Passwords: Argon2id hashes (OWASP's first choice); a stolen database does not reveal them.
Sessions: a random token in an HttpOnly cookie; only its SHA-256 is stored, so a leaked
database does not contain working sessions. Sessions can be ended at once (logout).
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

from helpdesk.domain.offices import OfficeId
from helpdesk.storage.db import Connection, token_hash

Role = Literal["staff", "admin"]

SESSION_HOURS = 8  # one working day
MIN_PASSWORD_LENGTH = 12
MAX_FAILURES_PER_EMAIL = 5  # wrong passwords per account ...
MAX_FAILURES_PER_IP = 20  # ... and per address, within:
FAILURE_WINDOW = timedelta(minutes=15)

hasher = PasswordHasher()  # Argon2id with the library's current recommended cost settings
# Checked when the email does not exist, so a wrong email takes as long as a wrong password
# (otherwise the response time would tell an attacker which emails are real).
DUMMY_HASH = hasher.hash("not a real password")


class TooManyAttempts(Exception):
    """Too many failed logins recently: wait before trying again."""


class Staff(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    office: OfficeId | None  # None for admins: they see every office
    demo: bool = False  # the demo account sees only demo tickets


def now() -> datetime:
    return datetime.now(UTC)


def create_staff(
    connection: Connection,
    email: str,
    name: str,
    role: Role,
    office: OfficeId | None,
    password: str,
) -> int:
    """Add a staff account (there is no public sign-up: tools/add_staff.py calls this)."""
    if (role == "staff") != (office is not None):
        raise ValueError("Staff need an office; admins must not have one (they see every office).")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"The password must have at least {MIN_PASSWORD_LENGTH} characters.")
    try:
        row = connection.execute(
            "INSERT INTO staff (email, name, role, office, password_hash)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (email.strip(), name, role, office, hasher.hash(password)),
        ).fetchone()
    except UniqueViolation as error:  # the unique index on lower(email)
        raise ValueError(f"{email} already has an account.") from error
    if row is None:  # RETURNING always gives the new row; checked so the type is a plain int
        raise RuntimeError("Postgres did not return the new staff id.")
    return int(row["id"])


def recent_failures(connection: Connection, key: str) -> int:
    row = connection.execute(
        "SELECT count(*) AS n FROM failed_logins WHERE key = %s AND at > %s",
        (key, now() - FAILURE_WINDOW),
    ).fetchone()
    return int(row["n"]) if row else 0


def authenticate(connection: Connection, email: str, password: str, ip: str) -> Staff | None:
    """The staff member if email and password match, else None. Raises TooManyAttempts first if
    this account or this address failed too often recently (even the right password waits)."""
    email_key, ip_key = f"email:{email.strip().lower()}", f"ip:{ip}"
    if (
        recent_failures(connection, email_key) >= MAX_FAILURES_PER_EMAIL
        or recent_failures(connection, ip_key) >= MAX_FAILURES_PER_IP
    ):
        raise TooManyAttempts
    row = connection.execute(
        "SELECT * FROM staff WHERE lower(email) = lower(%s)", (email.strip(),)
    ).fetchone()
    try:
        hasher.verify(row["password_hash"] if row else DUMMY_HASH, password)
        ok = row is not None
    except VerifyMismatchError:
        ok = False
    if not ok:
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO failed_logins (key) VALUES (%s)", [(email_key,), (ip_key,)]
            )
        return None
    return Staff.model_validate(row)


def create_session(connection: Connection, staff_id: int) -> str:
    """A new login session; returns the token for the cookie (only its hash is stored)."""
    token = secrets.token_urlsafe(32)  # 256 random bits: impossible to guess
    connection.execute(
        "INSERT INTO sessions (token_hash, staff_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash(token), staff_id, now() + timedelta(hours=SESSION_HOURS)),
    )
    return token


def staff_for_session(connection: Connection, token: str) -> Staff | None:
    """The logged-in staff member, or None if the token is unknown or expired."""
    row = connection.execute(
        "SELECT staff.* FROM sessions JOIN staff ON staff.id = sessions.staff_id"
        " WHERE sessions.token_hash = %s AND sessions.expires_at > now()",
        (token_hash(token),),
    ).fetchone()
    return Staff.model_validate(row) if row else None


def end_session(connection: Connection, token: str) -> None:
    """Logout: the token stops working at once."""
    connection.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash(token),))


DEMO_EMAIL = "demo@demo.invalid"  # .invalid is reserved: it can never be a real address


def demo_account(connection: Connection) -> Staff:
    """The demo staff member (created on first use). Its password is random and thrown away,
    so the account can only be entered through the demo button, never with a password."""
    row = connection.execute("SELECT * FROM staff WHERE demo").fetchone()
    if row is None:
        row = connection.execute(
            "INSERT INTO staff (email, name, role, office, password_hash, demo)"
            " VALUES (%s, 'Demo', 'admin', NULL, %s, true) RETURNING *",
            (DEMO_EMAIL, hasher.hash(secrets.token_urlsafe(32))),
        ).fetchone()
    return Staff.model_validate(row)
