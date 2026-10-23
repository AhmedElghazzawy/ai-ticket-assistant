"""Save every ticket in Postgres, so forwarded tickets reach staff in the review queue.

Postgres: locally in Docker (compose.yaml), in production Neon (free, EU). The database holds
student messages (personal data): its address and password are secrets (DATABASE_URL), never in git.
"""

import hashlib
import json
import os
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from decision import OFFICE_OF, OfficeId, Reason
from tickets import Category, Language, Priority

if TYPE_CHECKING:  # only for the type hint, so store.py does not load the AI pipeline
    from pipeline import TicketResult

Connection = psycopg.Connection[DictRow]  # rows come back as dictionaries
# A way to borrow a connection briefly (e.g. pool.connection), so slow AI calls never hold one.
Database = Callable[[], AbstractContextManager[Connection]]

# Read directly, like LOG_FORMAT, so the store works without the API key. The default is the
# local Docker database (compose.yaml); production sets DATABASE_URL to Neon's address.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://helpdesk:local-only@127.0.0.1:5433/helpdesk")

# The demo queue (tools/make_demo_tickets.py builds it from the dataset and its real results).
DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_tickets.json"

# Each step upgrades the database by one version, in order, each in one transaction. Existing data
# is kept. Never edit a released step: add a new one. (The SQLite history ended at version 4;
# Postgres is a new database, so its history starts again at 1.)
MIGRATIONS: dict[int, str] = {
    1: """
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;  -- pgvector, for the knowledge-base search

CREATE TABLE tickets (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- the number shown to the student
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    language    TEXT NOT NULL,
    text        TEXT NOT NULL,
    category    TEXT NOT NULL,
    priority    TEXT NOT NULL,
    escalate    BOOLEAN NOT NULL,
    ai_reason   TEXT NOT NULL,                      -- the model's own explanation of its labels
    office      TEXT NOT NULL,                      -- office ID: it, student_affairs, fees, sks, duty
    auto_send   BOOLEAN NOT NULL,
    reasons     JSONB NOT NULL,                     -- reason codes: why it was not auto-sent
    top_score   DOUBLE PRECISION NOT NULL,          -- the best document match
    draft       TEXT NOT NULL,                      -- the AI's grounded draft (a starting point for staff)
    covered     BOOLEAN NOT NULL,                   -- the documents answer the ticket
    sources     JSONB NOT NULL,                     -- cited sources (id, title, section, url)
    status      TEXT NOT NULL CHECK (status IN ('auto_sent', 'open', 'handled')),
    final_reply TEXT,                               -- what staff decided to answer
    handled_at  TIMESTAMPTZ,
    demo        BOOLEAN NOT NULL DEFAULT false      -- a sample ticket for the demo
);
CREATE INDEX tickets_queue ON tickets (demo, status, office);

CREATE TABLE staff (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         TEXT NOT NULL,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('staff', 'admin')),
    office        TEXT,                             -- office ID for staff; NULL for admins
    password_hash TEXT NOT NULL,                    -- Argon2id, never the password itself
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    demo          BOOLEAN NOT NULL DEFAULT false    -- the demo account
);
CREATE UNIQUE INDEX staff_email ON staff (lower(email));  -- Ayse@ and ayse@ are the same person

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,                    -- SHA-256 of the cookie value, never the value
    staff_id   BIGINT NOT NULL REFERENCES staff (id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE failed_logins (                      -- for the login rate limit
    key TEXT NOT NULL,                              -- "email:..." or "ip:..."
    at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX failed_logins_by_key ON failed_logins (key, at);
""",
    2: """
CREATE TABLE kb_chunks (                          -- the knowledge base, searchable by meaning
    id        TEXT PRIMARY KEY,                     -- e.g. "sinavlar.tr#3"
    doc       TEXT NOT NULL,                        -- e.g. "sinavlar": the same for TR and EN
    language  TEXT NOT NULL CHECK (language IN ('tr', 'en')),
    title     TEXT NOT NULL,
    source    TEXT NOT NULL,                        -- the official source, cited in answers
    url       TEXT NOT NULL,
    text      TEXT NOT NULL,
    embedding vector(768) NOT NULL                  -- gemini-embedding-2, length 1 (normalized)
);
-- No vector index (HNSW) on purpose: for ~100 rows an exact scan is fast and never misses.
""",
    3: """
-- The student's own view of a ticket (status, staff reply) and their feedback, both protected by
-- a secret code shown once to the student. Only its SHA-256 is stored; older rows have none.
ALTER TABLE tickets ADD COLUMN access_hash TEXT;
ALTER TABLE tickets ADD COLUMN feedback TEXT CHECK (feedback IN ('helpful', 'not_helpful'));
ALTER TABLE tickets ADD COLUMN feedback_at TIMESTAMPTZ;
""",
}
SCHEMA_VERSION = max(MIGRATIONS)

Status = Literal["auto_sent", "open", "handled"]


Feedback = Literal["helpful", "not_helpful"]


def token_hash(token: str) -> str:
    """SHA-256 of a secret (session token, ticket code): only this is stored, never the secret."""
    return hashlib.sha256(token.encode()).hexdigest()


class StoredSource(BaseModel):
    id: str  # e.g. "harc_ucretler.tr#5"
    title: str
    section: str
    source: str = ""  # the official source line, e.g. "Resmî olmayan kaynak: ..."; "" in older rows
    url: str


class StoredTicket(BaseModel):
    """One row, checked by pydantic: a broken row fails here, not later on the page."""

    id: int
    created_at: datetime
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
    handled_at: datetime | None
    demo: bool  # a sample ticket for the demo: never mixed with real visitors' tickets
    feedback: Feedback | None = None  # the student's thumbs up / down, if they gave one


def migrate(connection: Connection) -> None:
    """Bring the database up to SCHEMA_VERSION, keeping its data. Safe when several app
    instances start at once: a database lock lets only one of them migrate."""
    with connection.transaction():
        connection.execute("SELECT pg_advisory_xact_lock(7316)")  # any fixed number: our lock
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        row = connection.execute("SELECT max(version) AS version FROM schema_migrations").fetchone()
        current = row["version"] if row and row["version"] is not None else 0
        for step in sorted(n for n in MIGRATIONS if n > current):
            connection.execute(MIGRATIONS[step])  # our own SQL, never user input
            connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (step,))


def conninfo(url: str, schema: str | None) -> str:
    """The connection string; with a schema, our tables live there (tests use a fresh one each)."""
    return make_conninfo(url, options=f"-c search_path={schema},public") if schema else url


def connect(url: str = DATABASE_URL, schema: str | None = None) -> Connection:
    """One connection, upgraded to the current schema (for tools and tests; the API uses a pool)."""
    connection = psycopg.connect(conninfo(url, schema), row_factory=dict_row, autocommit=True)
    migrate(connection)
    return connection


def open_pool(url: str = DATABASE_URL, schema: str | None = None) -> ConnectionPool[Connection]:
    """A few connections kept open and reused: much faster than one new connection per request,
    especially to a cloud database (a new encrypted connection takes a while)."""
    pool: ConnectionPool[Connection] = ConnectionPool(
        conninfo(url, schema),
        connection_class=psycopg.Connection[DictRow],
        kwargs={"row_factory": dict_row, "autocommit": True},
        min_size=1,
        max_size=5,
        # Neon closes connections when its free database sleeps (~5 min idle): test each one
        # before use (one tiny query) and replace it if dead, instead of failing a request.
        check=ConnectionPool.check_connection,
        open=True,
    )
    with pool.connection() as connection:
        migrate(connection)
    return pool


def save_ticket(
    connection: Connection,
    text: str,
    language: Language,
    result: "TicketResult",
    access_hash: str | None = None,
) -> int:
    """Store one processed ticket and return its number. Auto-sent tickets are stored too (for statistics)."""
    c, decision, answer = result.classification, result.decision, result.answer
    cited = {chunk.id: chunk for _, chunk in result.hits}
    sources = [
        StoredSource(
            id=i,
            title=cited[i].title,
            section=cited[i].section,
            source=cited[i].source,
            url=cited[i].url,
        )
        for i in answer.sources
        if i in cited  # a cited id that was never retrieved is not shown (the decision flags it)
    ]
    row = connection.execute(
        "INSERT INTO tickets (language, text, category, priority, escalate, ai_reason, office,"
        " auto_send, reasons, top_score, draft, covered, sources, status, access_hash)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            language,
            text,
            c.category,
            c.priority,
            c.escalate,
            c.reason,
            OFFICE_OF[c.category],
            decision.auto_send,
            Jsonb([reason.model_dump() for reason in decision.reasons]),
            result.hits[0][0] if result.hits else 0.0,
            answer.reply,
            answer.covered,
            Jsonb([source.model_dump() for source in sources]),
            "auto_sent" if decision.auto_send else "open",
            access_hash,
        ),
    ).fetchone()  # %s placeholders: psycopg sends the values separately (no SQL injection)
    if row is None:  # RETURNING always gives the new row; checked so the type is a plain int
        raise RuntimeError("Postgres did not return the new ticket number.")
    return int(row["id"])


PRIORITY_ORDER = (
    "CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
)


def count_tickets_since(connection: Connection, since: datetime) -> int:
    """How many real (not demo) tickets arrived since this time (for the daily cap)."""
    row = connection.execute(
        "SELECT count(*) AS n FROM tickets WHERE NOT demo AND created_at >= %s", (since,)
    ).fetchone()
    return int(row["n"]) if row else 0


def list_tickets(
    connection: Connection, status: Status, office: OfficeId | None = None, demo: bool = False
) -> list[StoredTicket]:
    """Tickets with this status (only this office's, if given; real or demo, never both),
    most urgent first, then the longest wait first."""
    rows = connection.execute(
        "SELECT * FROM tickets"
        " WHERE status = %s AND (%s::text IS NULL OR office = %s) AND demo = %s"
        f" ORDER BY {PRIORITY_ORDER}, created_at, id",  # our own constant, not user input
        (status, office, office, demo),
    ).fetchall()
    return [StoredTicket.model_validate(row) for row in rows]


def get_ticket(connection: Connection, ticket_id: int) -> StoredTicket | None:
    """One ticket, or None if the number does not exist."""
    row = connection.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    return StoredTicket.model_validate(row) if row else None


def find_for_student(connection: Connection, ticket_id: int, code: str) -> StoredTicket | None:
    """The ticket, only with its secret code. A wrong code and an unknown number both give None."""
    row = connection.execute(
        "SELECT * FROM tickets WHERE id = %s AND access_hash = %s AND NOT demo",
        (ticket_id, token_hash(code)),
    ).fetchone()
    return StoredTicket.model_validate(row) if row else None


def save_feedback(connection: Connection, ticket_id: int, code: str, feedback: Feedback) -> bool:
    """The student's thumbs up / down (the last choice counts). False if number or code is wrong."""
    row = connection.execute(
        "UPDATE tickets SET feedback = %s, feedback_at = now()"
        " WHERE id = %s AND access_hash = %s AND NOT demo RETURNING id",
        (feedback, ticket_id, token_hash(code)),
    ).fetchone()
    return row is not None


def mark_handled(connection: Connection, ticket_id: int, final_reply: str) -> bool:
    """Staff finished this ticket. Returns False if it was not open any more. One atomic UPDATE:
    if two staff members send at the same moment, exactly one of them wins."""
    row = connection.execute(
        "UPDATE tickets SET status = 'handled', final_reply = %s, handled_at = now()"
        " WHERE id = %s AND status = 'open' RETURNING id",
        (final_reply, ticket_id),
    ).fetchone()
    return row is not None


def reassign(connection: Connection, ticket_id: int, office: OfficeId) -> None:
    """Staff moved the ticket to another office."""
    connection.execute("UPDATE tickets SET office = %s WHERE id = %s", (office, ticket_id))


def reset_demo_tickets(connection: Connection) -> int:
    """Put the demo queue back to its starting state (every demo login gets a fresh queue).
    Only demo rows are touched: real tickets are never changed."""
    samples: list[dict[str, Any]] = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    with connection.transaction():  # one transaction: the demo queue is never half-reset
        connection.execute("DELETE FROM tickets WHERE demo")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO tickets (created_at, language, text, category, priority, escalate,"
                " ai_reason, office, auto_send, reasons, top_score, draft, covered, sources,"
                " status, demo)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, %s, %s, %s, %s, %s, 'open', true)",
                [
                    (
                        now - timedelta(minutes=t["age_minutes"]),
                        t["language"],
                        t["text"],
                        t["category"],
                        t["priority"],
                        t["escalate"],
                        t["ai_reason"],
                        t["office"],
                        Jsonb(t["reasons"]),
                        t["top_score"],
                        t["draft"],
                        t["covered"],
                        Jsonb(t["sources"]),
                    )
                    for t in samples
                ],
            )
    return len(samples)
