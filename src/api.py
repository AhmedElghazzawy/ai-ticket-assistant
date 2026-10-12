"""The web API behind the student chat page.

Run: uv run uvicorn api:app --app-dir src     then open http://127.0.0.1:8000
"""

import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from sqlite3 import Connection
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from decision import OfficeId
from logs import configure, get_logger
from pipeline import process_ticket
from retrieval import load_index
from store import (
    DB_PATH,
    Status,
    StoredSource,
    StoredTicket,
    connect,
    get_ticket,
    list_tickets,
    mark_handled,
    reassign,
    save_ticket,
)
from tickets import Category, Priority

configure()
logger = get_logger(__name__)
# The built React app (cd frontend && npm run build). FastAPI serves it, so one server runs everything.
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
INDEX = load_index()  # the knowledge-base vectors, loaded once when the server starts
DB_FILE = DB_PATH  # the ticket database (tests point this to a temporary file)
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}  # testclient: pytest's fake client

app = FastAPI(
    title="BŞEÜ Helpdesk Assistant",
    # Short operation IDs ("staff_list", not "staff_list_api_staff_tickets_get"), so the generated
    # frontend functions get clean names (FastAPI's advice for client generation).
    generate_unique_id_function=lambda route: route.name,
)


SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")


@app.middleware("http")
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


@contextmanager
def database() -> Iterator[Connection]:
    """One short connection per request (requests run on different threads)."""
    with closing(connect(DB_FILE)) as connection:
        yield connection


class TicketIn(BaseModel):
    """What the page sends: the student's message and the page language."""

    text: str = Field(min_length=1, max_length=2000)
    language: Literal["tr", "en"]


class TicketOut(BaseModel):
    """What the student sees. `reply` is only filled when every safety check passed."""

    ticket_id: int  # shown to the student, so staff and student can refer to the same request
    category: Category
    priority: Priority
    office: OfficeId  # an ID: the page shows the name in the student's language
    auto_send: bool
    reply: str | None  # None: a human answers, so the unchecked draft never leaves the server
    sources: list[StoredSource]
    emergency: bool  # show the 112 line (urgent and escalated)


@app.get("/api/health")
def health() -> dict[str, str]:
    """For Docker and hosting services: the app is up and answering."""
    return {"status": "ok"}


@app.post("/api/tickets")
def create_ticket(ticket: TicketIn) -> TicketOut:
    """Run the whole pipeline for one student message."""
    try:
        r = process_ticket(ticket.text, ticket.language, INDEX)
    except Exception as error:  # show students a short message only
        # Only the error TYPE: an error message can contain the model's output, which may echo
        # the student's words (personal data never goes into logs).
        logger.error("pipeline_failed", error_type=type(error).__name__)
        raise HTTPException(
            status_code=503, detail="The assistant is not available right now."
        ) from error
    with database() as db:
        saved = get_ticket(db, save_ticket(db, ticket.text, ticket.language, r))
    if saved is None:  # cannot happen right after saving; checked so the type is exact
        raise HTTPException(status_code=500, detail="The ticket could not be saved.")
    logger.info(
        "ticket_created",
        ticket_id=saved.id,
        language=saved.language,
        text_length=len(saved.text),  # the length, never the text
        category=saved.category,
        priority=saved.priority,
        escalate=saved.escalate,
        office=saved.office,
        auto_send=saved.auto_send,
        reasons=[reason.code for reason in saved.reasons],
        top_score=round(saved.top_score, 4),
    )
    # The response is built from the SAVED ticket, so students and staff always see the same data.
    return TicketOut(
        ticket_id=saved.id,
        category=saved.category,
        priority=saved.priority,
        office=saved.office,
        auto_send=saved.auto_send,
        reply=saved.draft if saved.auto_send else None,
        sources=saved.sources if saved.auto_send else [],
        emergency=saved.escalate and saved.priority == "urgent",
    )


# ---------------------------------------------------------------- staff console


def local_only(request: Request) -> None:
    """Staff pages show student messages. Until staff login exists (roadmap Phase 12), they only
    answer requests from this computer, so the server can never expose them by accident."""
    host = request.client.host if request.client else ""
    if host not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Staff pages are only available locally.")


# Every staff endpoint runs local_only first. A router (not a separate app) keeps the staff
# endpoints in the same OpenAPI schema, which the frontend's types are generated from.
staff = APIRouter(prefix="/api/staff", tags=["staff"], dependencies=[Depends(local_only)])


class ReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)


class OfficeIn(BaseModel):
    office: OfficeId


def found(ticket: StoredTicket | None) -> StoredTicket:
    """The ticket, or a 404 answer if the number does not exist."""
    if ticket is None:
        raise HTTPException(status_code=404, detail="No ticket with this number.")
    return ticket


@staff.get("/tickets")
def staff_list(status: Status = "open") -> list[StoredTicket]:
    """The review queue: urgent first, then oldest first."""
    with database() as db:
        return list_tickets(db, status)


@staff.get("/tickets/{ticket_id}")
def staff_get(ticket_id: int) -> StoredTicket:
    with database() as db:
        return found(get_ticket(db, ticket_id))


@staff.post("/tickets/{ticket_id}/reply")
def staff_reply(ticket_id: int, body: ReplyIn) -> StoredTicket:
    """Send the staff reply and close the ticket. 409 if someone already handled it."""
    with database() as db:
        if found(get_ticket(db, ticket_id)).status != "open":
            raise HTTPException(status_code=409, detail="This ticket is already handled.")
        mark_handled(db, ticket_id, body.reply.strip())
        logger.info("staff_reply", ticket_id=ticket_id, reply_length=len(body.reply.strip()))
        return found(get_ticket(db, ticket_id))


@staff.patch("/tickets/{ticket_id}")
def staff_reassign(ticket_id: int, body: OfficeIn) -> StoredTicket:
    with database() as db:
        found(get_ticket(db, ticket_id))
        reassign(db, ticket_id, body.office)
        logger.info("staff_reassign", ticket_id=ticket_id, office=body.office)
        return found(get_ticket(db, ticket_id))


app.include_router(staff)  # after the staff endpoints above are defined


# ---------------------------------------------------------------- the web app


@app.get("/{path:path}", include_in_schema=False)
def web_app(path: str) -> FileResponse:
    """Files of the built React app; any other address gets index.html and the app's router
    picks the page (e.g. /staff/tickets/2). Registered last, so every /api route wins."""
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found.")
    index = DIST_DIR / "index.html"
    if not index.exists():
        raise HTTPException(
            status_code=404, detail="Frontend not built: cd frontend && npm run build"
        )
    file = (DIST_DIR / path).resolve()
    # Path traversal guard: "/../.env" must never leave the dist folder.
    if path and file.is_file() and file.is_relative_to(DIST_DIR.resolve()):
        return FileResponse(file)
    return FileResponse(index)
