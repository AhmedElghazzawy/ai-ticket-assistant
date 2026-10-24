"""Shared test setup, run automatically by pytest for every test.

Tests run against a REAL Postgres (locally: docker compose up -d db; in CI: a service container),
like production. Each test gets its own empty schema, dropped afterwards: tests never see each
other's data and never touch real data.
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from harness import Api, no_pipeline
from psycopg_pool import ConnectionPool

from helpdesk.api.app import create_app
from helpdesk.core.settings import AppSettings
from helpdesk.storage import db as store
from helpdesk.storage.db import Connection


@pytest.fixture(autouse=True)
def schema() -> Iterator[str]:
    """A fresh, empty schema for this test, dropped afterwards."""
    name = f"test_{uuid.uuid4().hex[:12]}"  # our own random name, not user input
    with psycopg.connect(store.database_url(), autocommit=True) as admin:
        admin.execute(f'CREATE SCHEMA "{name}"')
    yield name
    with psycopg.connect(store.database_url(), autocommit=True) as admin:
        admin.execute(f'DROP SCHEMA "{name}" CASCADE')


@pytest.fixture
def db(schema: str) -> Iterator[Connection]:
    """One connection to this test's schema, migrated to the current version."""
    connection = store.connect(None, schema)
    yield connection
    connection.close()


@pytest.fixture
def make_api(schema: str) -> Iterator[Callable[..., Api]]:
    """Build a test app with chosen settings, e.g. make_api(demo_mode=True). Its database is this
    test's schema; its pipeline must be chosen with api.use_pipeline (no Gemini calls)."""
    pools: list[ConnectionPool[Connection]] = []

    def open_pool() -> ConnectionPool[Connection]:
        pools.append(store.open_pool(None, schema))
        return pools[-1]

    def build(**settings: Any) -> Api:
        settings_ = AppSettings(_env_file=None, **settings)
        return Api(create_app(settings_, pipeline=no_pipeline, open_pool=open_pool))

    yield build
    for pool in pools:
        pool.close()


@pytest.fixture
def api(make_api: Callable[..., Api]) -> Api:
    """A test app with the default settings."""
    return make_api()
