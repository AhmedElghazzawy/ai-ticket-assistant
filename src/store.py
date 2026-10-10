"""Save every ticket in a small SQLite database, so forwarded tickets reach staff in the review queue.

The database file holds student messages (personal data): it is in .gitignore and must never be committed.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for the type hint, so store.py does not load the AI pipeline
    from pipeline import TicketResult

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "helpdesk.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- the ticket number shown to the student
    created_at  TEXT NOT NULL,
    language    TEXT NOT NULL,
    text        TEXT NOT NULL,
    category    TEXT NOT NULL,
    priority    TEXT NOT NULL,
    escalate    INTEGER NOT NULL,                   -- SQLite has no true/false: 1 or 0
    office      TEXT NOT NULL,
    auto_send   INTEGER NOT NULL,
    reasons     TEXT NOT NULL,                      -- JSON list: why it was not auto-sent
    draft       TEXT NOT NULL,                      -- the AI's grounded draft (a starting point for staff)
    sources     TEXT NOT NULL,                      -- JSON list of cited chunk ids
    status      TEXT NOT NULL,                      -- 'auto_sent', 'open' or 'handled'
    final_reply TEXT,                               -- what staff decided to answer
    handled_at  TEXT
)"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database (creating the file and table if needed). Rows behave like dictionaries."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    return connection


def save_ticket(connection: sqlite3.Connection, text: str, language: str, result: "TicketResult", office: str) -> int:
    """Store one processed ticket and return its number. Auto-sent tickets are stored too (for statistics)."""
    c, decision = result.classification, result.decision
    cursor = connection.execute(
        "INSERT INTO tickets (created_at, language, text, category, priority, escalate, office, auto_send,"
        " reasons, draft, sources, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), language, text, c.category, c.priority, int(c.escalate),
         office, int(decision.auto_send), json.dumps(decision.reasons), result.answer.reply,
         json.dumps(result.answer.sources), "auto_sent" if decision.auto_send else "open"),
    )  # the ? placeholders let SQLite insert the values safely (no SQL injection)
    connection.commit()
    return cursor.lastrowid


PRIORITY_ORDER = "CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"


def list_tickets(connection: sqlite3.Connection, status: str) -> list[sqlite3.Row]:
    """Tickets with this status, most urgent first, then oldest first."""
    return connection.execute(
        f"SELECT * FROM tickets WHERE status = ? ORDER BY {PRIORITY_ORDER}, id", (status,)
    ).fetchall()


def mark_handled(connection: sqlite3.Connection, ticket_id: int, final_reply: str) -> None:
    """Staff finished this ticket: save their final reply and the time."""
    connection.execute(
        "UPDATE tickets SET status = 'handled', final_reply = ?, handled_at = ? WHERE id = ?",
        (final_reply, datetime.now().isoformat(timespec="seconds"), ticket_id),
    )
    connection.commit()
