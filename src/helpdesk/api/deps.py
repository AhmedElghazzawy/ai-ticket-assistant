"""What every endpoint can ask for: the app's services and the logged-in staff member.

FastAPI "dependencies": an endpoint declares `services: ServicesDep` and FastAPI hands it the
services of the app that received the request. Nothing lives in module globals, so each test
builds its own app (own database schema, own counters, fake pipeline) without patching modules.
"""

import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from psycopg_pool import ConnectionPool

from helpdesk import auth
from helpdesk.api.security import RateLimiter
from helpdesk.auth import Staff
from helpdesk.core.settings import AppSettings
from helpdesk.pipeline import TicketResult
from helpdesk.storage.db import Connection, Database

# One ticket through the whole assistant: (text, language, database) -> result.
Pipeline = Callable[[str, str, Database], TicketResult]

COOKIE_NAME = "helpdesk_session"


class LazyPool:
    """The connection pool, opened on the first request (startup stays fast and needs no
    database), closed when the app stops."""

    def __init__(self, open_pool: Callable[[], ConnectionPool[Connection]]) -> None:
        self.open_pool = open_pool
        self.pool: ConnectionPool[Connection] | None = None
        # Two first requests at the same moment must not open two pools.
        self.lock = threading.Lock()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        """A connection from the pool for one request, given back afterwards."""
        with self.lock:
            if self.pool is None:  # first request: open the pool, update the schema, sync the KB
                self.pool = self.open_pool()
        with self.pool.connection() as connection:
            yield connection

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()


@dataclass
class Services:
    """Everything one app instance owns. Built once in create_app()."""

    settings: AppSettings
    pipeline: Pipeline
    pool: LazyPool
    dist_dir: Path  # the built React app
    ticket_limiter: RateLimiter = field(default_factory=RateLimiter)
    # Looking up a ticket or giving feedback costs no AI call, so the limit is generous, but a
    # public endpoint is never unlimited (database load, guessing).
    lookup_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(((30, 60.0),)))

    def database(self) -> Database:
        return self.pool.connection


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


def current_staff(request: Request, services: ServicesDep) -> Staff:
    """The logged-in staff member, or 401. Every staff endpoint depends on this."""
    token = request.cookies.get(COOKIE_NAME)
    with services.pool.connection() as db:
        staff_member = auth.staff_for_session(db, token) if token else None
    if staff_member is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return staff_member


# FastAPI's recommended form: endpoints just declare `staff_member: CurrentStaff`.
CurrentStaff = Annotated[Staff, Depends(current_staff)]
