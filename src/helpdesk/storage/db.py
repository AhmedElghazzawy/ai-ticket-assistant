"""Postgres connections and the schema: every ticket and staff account lives here.

Postgres: locally in Docker (compose.yaml), in production Neon (free, EU). The database holds
student messages (personal data): its address and password are secrets (DATABASE_URL), never in git.
"""

import hashlib
from collections.abc import Callable
from contextlib import AbstractContextManager

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

from helpdesk.core.settings import get_app_settings

Connection = psycopg.Connection[DictRow]  # rows come back as dictionaries
# A way to borrow a connection briefly (e.g. pool.connection), so slow AI calls never hold one.
Database = Callable[[], AbstractContextManager[Connection]]

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


def token_hash(token: str) -> str:
    """SHA-256 of a secret (session token, ticket code): only this is stored, never the secret."""
    return hashlib.sha256(token.encode()).hexdigest()


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


def database_url() -> str:
    """DATABASE_URL from the settings: the local Docker database by default, Neon in production."""
    return get_app_settings().database_url.get_secret_value()


def connect(url: str | None = None, schema: str | None = None) -> Connection:
    """One connection, upgraded to the current schema (for tools and tests; the API uses a pool)."""
    connection = psycopg.connect(
        conninfo(url or database_url(), schema), row_factory=dict_row, autocommit=True
    )
    migrate(connection)
    return connection


def open_pool(url: str | None = None, schema: str | None = None) -> ConnectionPool[Connection]:
    """A few connections kept open and reused: much faster than one new connection per request,
    especially to a cloud database (a new encrypted connection takes a while)."""
    pool: ConnectionPool[Connection] = ConnectionPool(
        conninfo(url or database_url(), schema),
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
