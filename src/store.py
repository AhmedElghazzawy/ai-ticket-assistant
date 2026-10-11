"""Save every ticket in a small SQLite database, so forwarded tickets reach staff in the review queue.

The database file holds student messages (personal data): it is in .gitignore and must never be committed.
"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from decision import OFFICE_OF, OfficeId, Reason
from tickets import Category, Language, Priority

if TYPE_CHECKING:  # only for the type hint, so store.py does not load the AI pipeline
    from pipeline import TicketResult

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "helpdesk.db"

SCHEMA_VERSION = 2  # raise it whenever the table changes (2: office IDs, reason codes, sources)
SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- the ticket number shown to the student
    created_at  TEXT NOT NULL,
    language    TEXT NOT NULL,
    text        TEXT NOT NULL,
    category    TEXT NOT NULL,
    priority    TEXT NOT NULL,
    escalate    INTEGER NOT NULL,                   -- SQLite has no true/false: 1 or 0
    ai_reason   TEXT NOT NULL,                      -- the model's own explanation of its labels
    office      TEXT NOT NULL,                      -- office ID: it, student_affairs, fees, sks, duty
    auto_send   INTEGER NOT NULL,
    reasons     TEXT NOT NULL,                      -- JSON list of reason codes: why it was not auto-sent
    top_score   REAL NOT NULL,                      -- the best document match
    draft       TEXT NOT NULL,                      -- the AI's grounded draft (a starting point for staff)
    covered     INTEGER NOT NULL,                   -- 1: the documents answer the ticket
    sources     TEXT NOT NULL,                      -- JSON list of cited sources (id, title, section, url)
    status      TEXT NOT NULL,                      -- 'auto_sent', 'open' or 'handled'
    final_reply TEXT,                               -- what staff decided to answer
    handled_at  TEXT
)"""

Status = Literal["auto_sent", "open", "handled"]


class StoredSource(BaseModel):
    id: str  # e.g. "harc_ucretler.tr#5"
    title: str
    section: str
    url: str


class StoredTicket(BaseModel):
    """One row, checked by pydantic: a broken row fails here, not later on the page."""

    id: int
    created_at: str
    language: Language
    text: str
    category: Category
    priority: Priority
    escalate: bool
    ai_reason: str
    office: OfficeId
    auto_send: bool
    reasons: list[Reason]
    top_score: float
    draft: str
    covered: bool
    sources: list[StoredSource]
    status: Status
    final_reply: str | None
    handled_at: str | None


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database, creating it if needed. An older database file is refused with a clear message."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'tickets'").fetchone()
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if exists and version != SCHEMA_VERSION:
        connection.close()
        raise RuntimeError(
            f"{db_path.name} has schema version {version}, this code needs {SCHEMA_VERSION}. "
            "It only holds local test tickets: delete the file and it is created again."
        )
    connection.execute(SCHEMA)
    connection.execute(
        f"PRAGMA user_version = {SCHEMA_VERSION}"
    )  # our own constant, not user input
    return connection


def save_ticket(
    connection: sqlite3.Connection, text: str, language: Language, result: "TicketResult"
) -> int:
    """Store one processed ticket and return its number. Auto-sent tickets are stored too (for statistics)."""
    c, decision, answer = result.classification, result.decision, result.answer
    cited = {chunk.id: chunk for _, chunk in result.hits}
    sources = [
        StoredSource(id=i, title=cited[i].title, section=cited[i].section, url=cited[i].url)
        for i in answer.sources
        if i in cited  # a cited id that was never retrieved is not shown (the decision flags it)
    ]
    cursor = connection.execute(
        "INSERT INTO tickets (created_at, language, text, category, priority, escalate, ai_reason,"
        " office, auto_send, reasons, top_score, draft, covered, sources, status)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now(UTC).isoformat(timespec="seconds"),
            language,
            text,
            c.category,
            c.priority,
            int(c.escalate),
            c.reason,
            OFFICE_OF[c.category],
            int(decision.auto_send),
            json.dumps([reason.model_dump() for reason in decision.reasons]),
            result.hits[0][0] if result.hits else 0.0,
            answer.reply,
            int(answer.covered),
            json.dumps([source.model_dump() for source in sources], ensure_ascii=False),
            "auto_sent" if decision.auto_send else "open",
        ),
    )  # the ? placeholders let SQLite insert the values safely (no SQL injection)
    connection.commit()
    if cursor.lastrowid is None:  # always set after an INSERT; checked so the type is a plain int
        raise RuntimeError("SQLite did not return the new ticket number.")
    return cursor.lastrowid


def to_ticket(row: sqlite3.Row) -> StoredTicket:
    """A database row as a checked StoredTicket (JSON columns parsed)."""
    values = dict(row)
    values["reasons"] = json.loads(values["reasons"])
    values["sources"] = json.loads(values["sources"])
    return StoredTicket.model_validate(values)


PRIORITY_ORDER = (
    "CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
)


def list_tickets(connection: sqlite3.Connection, status: Status) -> list[StoredTicket]:
    """Tickets with this status, most urgent first, then oldest first."""
    rows = connection.execute(
        f"SELECT * FROM tickets WHERE status = ? ORDER BY {PRIORITY_ORDER}, id", (status,)
    ).fetchall()
    return [to_ticket(row) for row in rows]


def get_ticket(connection: sqlite3.Connection, ticket_id: int) -> StoredTicket | None:
    """One ticket, or None if the number does not exist."""
    row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return to_ticket(row) if row else None


def mark_handled(connection: sqlite3.Connection, ticket_id: int, final_reply: str) -> None:
    """Staff finished this ticket: save their final reply and the time."""
    connection.execute(
        "UPDATE tickets SET status = 'handled', final_reply = ?, handled_at = ? WHERE id = ?",
        (final_reply, datetime.now(UTC).isoformat(timespec="seconds"), ticket_id),
    )
    connection.commit()


def reassign(connection: sqlite3.Connection, ticket_id: int, office: OfficeId) -> None:
    """Staff moved the ticket to another office."""
    connection.execute("UPDATE tickets SET office = ? WHERE id = ?", (office, ticket_id))
    connection.commit()
