"""The web API behind the student chat page.

Run: uv run uvicorn api:app --app-dir src     then open http://127.0.0.1:8000
"""

import logging
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from sqlite3 import Connection
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from decision import OfficeId
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

logger = logging.getLogger(__name__)  # log lines say they come from this file
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


@app.post("/api/tickets")
def create_ticket(ticket: TicketIn) -> TicketOut:
    """Run the whole pipeline for one student message."""
    try:
        r = process_ticket(ticket.text, ticket.language, INDEX)
    except Exception as error:  # log the details for us, show students a short message only
        logger.exception("process_ticket failed")
        raise HTTPException(
            status_code=503, detail="The assistant is not available right now."
        ) from error
    with database() as db:
        saved = get_ticket(db, save_ticket(db, ticket.text, ticket.language, r))
    if saved is None:  # cannot happen right after saving; checked so the type is exact
        raise HTTPException(status_code=500, detail="The ticket could not be saved.")
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
        return found(get_ticket(db, ticket_id))


@staff.patch("/tickets/{ticket_id}")
def staff_reassign(ticket_id: int, body: OfficeIn) -> StoredTicket:
    with database() as db:
        found(get_ticket(db, ticket_id))
        reassign(db, ticket_id, body.office)
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
