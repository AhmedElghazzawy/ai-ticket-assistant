"""Shared test setup, run automatically by pytest for every test.

Tests run against a REAL Postgres (locally: docker compose up -d db; in CI: a service container),
like production. Each test gets its own empty schema, dropped afterwards: tests never see each
other's data and never touch real data.
"""

import uuid
from collections.abc import Iterator

import psycopg
import pytest

import api
import store
from store import Connection


@pytest.fixture(autouse=True)
def fresh_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with empty per-visitor counters, so tests never limit each other."""
    monkeypatch.setattr(api, "ticket_limiter", api.RateLimiter())


@pytest.fixture(autouse=True)
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Connection]:
    """A fresh, migrated schema for this test; the API's pool points at it too."""
    schema = f"test_{uuid.uuid4().hex[:12]}"  # our own random name, not user input
    with psycopg.connect(store.DATABASE_URL, autocommit=True) as admin:
        admin.execute(f'CREATE SCHEMA "{schema}"')
    connection = store.connect(store.DATABASE_URL, schema)
    pool = store.open_pool(store.DATABASE_URL, schema)
    monkeypatch.setattr(api, "pool", pool)
    yield connection
    pool.close()
    connection.close()
    with psycopg.connect(store.DATABASE_URL, autocommit=True) as admin:
        admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
