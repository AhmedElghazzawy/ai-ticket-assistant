"""The web API behind the student chat page and the staff console.

Run: make serve     (uvicorn helpdesk.api.app:create_app --factory --reload)
     then open http://127.0.0.1:8000

create_app() is an "app factory": it builds a new app from its settings and services. Production
calls it once; each test calls it with its own database schema and a fake pipeline.
"""

import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, Response
from psycopg_pool import ConnectionPool

from helpdesk.ai.gemini import GeminiProvider
from helpdesk.api.deps import LazyPool, Pipeline, Services
from helpdesk.api.routers import login, staff, tickets, web
from helpdesk.core.logs import configure, get_logger
from helpdesk.core.paths import ROOT
from helpdesk.core.settings import AppSettings, get_app_settings
from helpdesk.pipeline import process_ticket
from helpdesk.retrieval.search import load_index, open_synced_pool
from helpdesk.storage.db import Connection

logger = get_logger(__name__)
# The built React app (cd frontend && npm run build). FastAPI serves it, so one server runs everything.
DIST_DIR = ROOT / "frontend" / "dist"
SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """One log line per request, and a request ID that ties together every log line it causes.
    A caller may send its own X-Request-ID; it is only accepted if it looks harmless."""
    given = request.headers.get("x-request-id", "")
    request_id = given if SAFE_REQUEST_ID.fullmatch(given) else uuid.uuid4().hex[:12]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,  # the path only: query strings can hold search text
        status=response.status_code,
        ms=round((time.perf_counter() - started) * 1000),
    )
    response.headers["X-Request-ID"] = request_id
    return response


def create_app(
    settings: AppSettings | None = None,
    *,
    pipeline: Pipeline | None = None,
    open_pool: Callable[[], ConnectionPool[Connection]] = open_synced_pool,
    dist_dir: Path = DIST_DIR,
) -> FastAPI:
    """Build the app. Every argument has the production default (the pipeline: Gemini); tests
    pass their own."""
    settings = settings or get_app_settings()  # a bad setting stops the app here, before serving
    configure(settings.log_format)
    load_index()  # fail at startup, not on the first ticket, if the search index is out of date
    services = Services(
        settings=settings,
        pipeline=pipeline or partial(process_ticket, llm=GeminiProvider()),
        pool=LazyPool(open_pool),
        dist_dir=dist_dir,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        services.pool.close()  # give the database connections back when the server stops

    app = FastAPI(
        title="BŞEÜ Helpdesk Assistant",
        lifespan=lifespan,
        # Short operation IDs ("staff_list", not "staff_list_api_staff_tickets_get"), so the
        # generated frontend functions get clean names (FastAPI's advice for client generation).
        generate_unique_id_function=lambda route: route.name,
    )
    app.state.services = services
    app.middleware("http")(log_requests)
    for router in (tickets.router, login.router, staff.router, web.router):  # web last: catch-all
        app.include_router(router)
    return app
