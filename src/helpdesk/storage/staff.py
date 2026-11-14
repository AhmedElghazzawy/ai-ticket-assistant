"""The staff, sessions and failed_logins tables. SQL only: the security rules (hashing, lockout,
session length) live in services/auth.py."""

from datetime import datetime

from psycopg.errors import UniqueViolation

from helpdesk.domain.offices import OfficeId
from helpdesk.domain.staff import Role, Staff
from helpdesk.storage.db import Connection


class EmailTaken(Exception):
    """Another account already uses this email (the unique index on lower(email))."""


def insert_staff(
    connection: Connection,
    email: str,
    name: str,
    role: Role,
    office: OfficeId | None,
    password_hash: str,
    demo: bool = False,
) -> Staff:
    try:
        row = connection.execute(
            "INSERT INTO staff (email, name, role, office, password_hash, demo)"
            " VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
            (email, name, role, office, password_hash, demo),
        ).fetchone()
    except UniqueViolation as error:
        raise EmailTaken(email) from error
    if row is None:  # RETURNING always gives the new row; checked so the type is exact
        raise RuntimeError("Postgres did not return the new staff row.")
    return Staff.model_validate(row)


def find_by_email(connection: Connection, email: str) -> tuple[Staff, str] | None:
    """The staff member and their password hash, or None. Emails match case-insensitively."""
    row = connection.execute(
        "SELECT * FROM staff WHERE lower(email) = lower(%s)", (email,)
    ).fetchone()
    return (Staff.model_validate(row), str(row["password_hash"])) if row else None


def find_demo(connection: Connection) -> Staff | None:
    row = connection.execute("SELECT * FROM staff WHERE demo").fetchone()
    return Staff.model_validate(row) if row else None


def count_failures(connection: Connection, key: str, since: datetime) -> int:
    row = connection.execute(
        "SELECT count(*) AS n FROM failed_logins WHERE key = %s AND at > %s", (key, since)
    ).fetchone()
    return int(row["n"]) if row else 0


def record_failures(connection: Connection, keys: list[str]) -> None:
    with connection.cursor() as cursor:
        cursor.executemany("INSERT INTO failed_logins (key) VALUES (%s)", [(k,) for k in keys])


def insert_session(
    connection: Connection, token_hash: str, staff_id: int, expires_at: datetime
) -> None:
    connection.execute(
        "INSERT INTO sessions (token_hash, staff_id, expires_at) VALUES (%s, %s, %s)",
        (token_hash, staff_id, expires_at),
    )


def staff_for_token_hash(connection: Connection, token_hash: str) -> Staff | None:
    """The staff member of a session that has not expired."""
    row = connection.execute(
        "SELECT staff.* FROM sessions JOIN staff ON staff.id = sessions.staff_id"
        " WHERE sessions.token_hash = %s AND sessions.expires_at > now()",
        (token_hash,),
    ).fetchone()
    return Staff.model_validate(row) if row else None


def delete_session(connection: Connection, token_hash: str) -> None:
    connection.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
