"""Staff accounts, passwords and login sessions: the security rules. The SQL is in storage/staff.py.

Passwords: Argon2id hashes (OWASP's first choice); a stolen database does not reveal them.
Sessions: a random token in an HttpOnly cookie; only its SHA-256 is stored, so a leaked
database does not contain working sessions. Sessions can be ended at once (logout).
"""

import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from helpdesk.domain.offices import OfficeId
from helpdesk.domain.staff import Role, Staff
from helpdesk.storage import staff as store
from helpdesk.storage.db import Connection, token_hash

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
        staff_member = store.insert_staff(
            connection, email.strip(), name, role, office, hasher.hash(password)
        )
    except store.EmailTaken as error:
        raise ValueError(f"{email} already has an account.") from error
    return staff_member.id


def authenticate(connection: Connection, email: str, password: str, ip: str) -> Staff | None:
    """The staff member if email and password match, else None. Raises TooManyAttempts first if
    this account or this address failed too often recently (even the right password waits)."""
    email_key, ip_key = f"email:{email.strip().lower()}", f"ip:{ip}"
    since = now() - FAILURE_WINDOW
    if (
        store.count_failures(connection, email_key, since) >= MAX_FAILURES_PER_EMAIL
        or store.count_failures(connection, ip_key, since) >= MAX_FAILURES_PER_IP
    ):
        raise TooManyAttempts
    found = store.find_by_email(connection, email.strip())
    try:
        hasher.verify(found[1] if found else DUMMY_HASH, password)
        ok = found is not None
    except VerifyMismatchError:
        ok = False
    if not ok or found is None:
        store.record_failures(connection, [email_key, ip_key])
        return None
    return found[0]


def create_session(connection: Connection, staff_id: int) -> str:
    """A new login session; returns the token for the cookie (only its hash is stored)."""
    token = secrets.token_urlsafe(32)  # 256 random bits: impossible to guess
    store.insert_session(
        connection, token_hash(token), staff_id, now() + timedelta(hours=SESSION_HOURS)
    )
    return token


def staff_for_session(connection: Connection, token: str) -> Staff | None:
    """The logged-in staff member, or None if the token is unknown or expired."""
    return store.staff_for_token_hash(connection, token_hash(token))


def end_session(connection: Connection, token: str) -> None:
    """Logout: the token stops working at once."""
    store.delete_session(connection, token_hash(token))


DEMO_EMAIL = "demo@demo.invalid"  # .invalid is reserved: it can never be a real address


def demo_account(connection: Connection) -> Staff:
    """The demo staff member (created on first use). Its password is random and thrown away,
    so the account can only be entered through the demo button, never with a password."""
    return store.find_demo(connection) or store.insert_staff(
        connection, DEMO_EMAIL, "Demo", "admin", None, hasher.hash(secrets.token_urlsafe(32)), True
    )
