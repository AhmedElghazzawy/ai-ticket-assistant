"""The web API behind the student chat page.

Run: .venv/bin/uvicorn api:app --app-dir src     then open http://127.0.0.1:8000
"""

import logging
from contextlib import closing
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from decision import UNITS
from pipeline import process_ticket
from retrieval import load_index
from store import DB_PATH, connect, save_ticket

logger = logging.getLogger(__name__)  # log lines say they come from this file
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
INDEX = load_index()  # the knowledge-base vectors, loaded once when the server starts
DB_FILE = DB_PATH  # the ticket database (tests point this to a temporary file)

app = FastAPI(title="BŞEÜ Helpdesk Assistant")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")  # serves style.css and app.js


class TicketIn(BaseModel):
    """What the page sends: the student's message and the page language."""

    text: str = Field(min_length=1, max_length=2000)
    language: Literal["tr", "en"]


class Source(BaseModel):
    """One cited rule: the document title and the section (with its article)."""

    title: str
    section: str


class TicketOut(BaseModel):
    """What the page shows. `reply` is only filled when every safety check passed."""

    ticket_id: int  # shown to the student, so staff and student can refer to the same request
    category: str
    priority: str
    office: str
    auto_send: bool
    reply: str | None  # None: a human answers, so the unchecked draft never leaves the server
    sources: list[Source]
    emergency: bool  # show the 112 line (urgent and escalated)


@app.get("/")
def home() -> FileResponse:
    """The student chat page."""
    return FileResponse(WEB_DIR / "index.html")


@app.post("/api/tickets")
def create_ticket(ticket: TicketIn) -> TicketOut:
    """Run the whole pipeline for one student message."""
    try:
        r = process_ticket(ticket.text, ticket.language, INDEX)
    except Exception as error:  # log the details for us, show students a short message only
        logger.exception("process_ticket failed")
        raise HTTPException(status_code=503, detail="The assistant is not available right now.") from error
    c = r.classification
    office = UNITS[ticket.language][c.category]
    with closing(connect(DB_FILE)) as db:  # one short connection per request (requests run on different threads)
        ticket_id = save_ticket(db, ticket.text, ticket.language, r, office)
    cited = {chunk.id: chunk for _, chunk in r.hits}
    sources = [Source(title=cited[s].title, section=cited[s].text.splitlines()[0]) for s in r.answer.sources]
    return TicketOut(
        ticket_id=ticket_id,
        category=c.category,
        priority=c.priority,
        office=office,
        auto_send=r.decision.auto_send,
        reply=r.answer.reply if r.decision.auto_send else None,
        sources=sources if r.decision.auto_send else [],
        emergency=c.escalate and c.priority == "urgent",
    )
