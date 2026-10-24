"""The web API behind the student chat page.

Run: make serve     then open http://127.0.0.1:8000
"""

import os
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Annotated, Literal, get_args
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field, field_validator

from helpdesk import auth
from helpdesk.auth import Staff
from helpdesk.core.logs import configure, get_logger
from helpdesk.core.paths import ROOT
from helpdesk.domain.decision import MIN_SCORE, Decision, Reason, show_first_help
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.tickets import Category, Priority
from helpdesk.insights import Insights, summarize
from helpdesk.pipeline import process_ticket
from helpdesk.retrieval.search import load_index, open_synced_pool
from helpdesk.storage.db import Connection, token_hash
from helpdesk.storage.tickets import (
    Status,
    StoredSource,
    StoredTicket,
    count_tickets_since,
    find_for_student,
    get_ticket,
    list_tickets,
    mark_handled,
    reassign,
    reset_demo_tickets,
    save_feedback,
    save_ticket,
)

configure()
logger = get_logger(__name__)
# The built React app (cd frontend && npm run build). FastAPI serves it, so one server runs everything.
DIST_DIR = ROOT / "frontend" / "dist"
load_index()  # fail at startup, not on the first ticket, if the search index is out of date
pool: ConnectionPool[Connection] | None = None  # opened on first use (tests replace it)
pool_lock = threading.Lock()

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
    """A connection from the pool for one request, given back afterwards."""
    global pool
    with pool_lock:  # two first requests at the same moment must not open two pools
        if pool is None:  # first request: open the pool, update the schema, sync the knowledge base
            pool = open_synced_pool()
    with pool.connection() as connection:
        yield connection


class TicketIn(BaseModel):
    """What the page sends: the student's message and the page language."""

    text: str = Field(min_length=1, max_length=2000)
    language: Literal["tr", "en"]

    @field_validator("text")
    @classmethod
    def clean_text(cls, text: str) -> str:
        """Trimmed; blank text and NUL characters (Postgres cannot store them) are refused here,
        before any Gemini call is paid for (Phase 11 stress tests)."""
        text = text.strip()
        if not text:
            raise ValueError("the message is blank")
        if "\x00" in text:
            raise ValueError("the message contains a NUL character")
        return text


class TicketOut(BaseModel):
    """What the student sees. `reply` is filled only for an auto-sent answer or a safe first help."""

    ticket_id: int  # shown to the student, so staff and student can refer to the same request
    category: Category
    priority: Priority
    office: OfficeId  # an ID: the page shows the name in the student's language
    auto_send: bool
    first_help: bool  # forwarded, but the cited draft helps now (decision.show_first_help)
    reply: str | None  # None: a human answers, so the unchecked draft never leaves the server
    sources: list[StoredSource]
    emergency: bool  # show the 112 line (urgent and escalated)
    access_code: str  # shown ONCE: with it, only this student can see the status and give feedback
    # "Nasıl karar verildi?": the checks behind the decision (never the draft or the model's text)
    reasons: list[Reason]  # failed checks; empty when the answer was sent automatically
    top_score: float  # the best document match
    min_score: float  # the threshold it is compared with


class RateLimiter:
    """Per-visitor limits, counted in memory only: an IP address is personal data, so it is never
    written to disk or logs. Resets on restart and works for one server: fine for our single
    machine (several servers would need a shared counter, e.g. Redis)."""

    def __init__(self, limits: tuple[tuple[int, float], ...] = ((5, 60.0), (30, 86_400.0))):
        self.limits = limits  # (how many, within how many seconds)
        self.seen: defaultdict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()  # requests run on several threads at once

    def allow(self, visitor: str) -> bool:
        now = time.monotonic()
        longest = max(window for _, window in self.limits)
        with self.lock:
            times = self.seen[visitor]
            while times and now - times[0] > longest:  # forget what is too old to matter
                times.popleft()
            if any(sum(now - t < window for t in times) >= most for most, window in self.limits):
                return False
            times.append(now)
            return True


# Behind a hosting proxy every request seems to come from the proxy. CLIENT_IP_HEADER names the
# header in which the proxy puts the real visitor (Render: "CF-Connecting-IP"). Empty (default): the
# header is ignored, because a visitor could fake it. NOT X-Forwarded-For with "trust all": its
# left-most address is written by the visitor, so a bot could invent a new address every time.
CLIENT_IP_HEADER = os.getenv("CLIENT_IP_HEADER", "").lower()


def client_ip(request: Request) -> str:
    """The visitor's address, for rate limits only (never stored or logged)."""
    if CLIENT_IP_HEADER and (forwarded := request.headers.get(CLIENT_IP_HEADER)):
        return forwarded.strip()
    return request.client.host if request.client else "unknown"


ticket_limiter = RateLimiter()
# The whole system's ceiling per day (UTC): at ~$0.0074 per ticket, 300 tickets cost at most
# ~$2.20 a day at paid prices, whatever bots do.
DAILY_TICKET_CAP = int(os.getenv("DAILY_TICKET_CAP", "300"))


# Looking up a ticket or giving feedback costs no AI call, so the limit is generous, but a public
# endpoint is never unlimited (database load, guessing).
lookup_limiter = RateLimiter(((30, 60.0),))


def check_lookup_limits(request: Request) -> None:
    if not lookup_limiter.allow(client_ip(request)):
        logger.info("lookup_rate_limited")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")


def check_ticket_limits(request: Request) -> None:
    """Runs BEFORE the pipeline, so a refused request never costs a Gemini call."""
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with database() as db:
        if count_tickets_since(db, midnight) >= DAILY_TICKET_CAP:
            logger.warning("daily_cap_reached", cap=DAILY_TICKET_CAP)
            raise HTTPException(
                status_code=429, detail="The assistant is busy today. Try tomorrow."
            )
    if not ticket_limiter.allow(client_ip(request)):
        logger.info("visitor_rate_limited")  # never the address itself
        raise HTTPException(status_code=429, detail="Too many questions. Please wait a minute.")


@app.get("/api/health")
def health() -> dict[str, str]:
    """For Docker and hosting services: the app is up and answering."""
    return {"status": "ok"}


@app.post("/api/tickets", dependencies=[Depends(check_ticket_limits)])
def create_ticket(ticket: TicketIn) -> TicketOut:
    """Run the whole pipeline for one student message."""
    try:
        r = process_ticket(ticket.text, ticket.language, database)
    except Exception as error:  # show students a short message only
        # Only the error TYPE: an error message can contain the model's output, which may echo
        # the student's words (personal data never goes into logs).
        logger.error("pipeline_failed", error_type=type(error).__name__)
        raise HTTPException(
            status_code=503, detail="The assistant is not available right now."
        ) from error
    code = secrets.token_urlsafe(16)  # 128 random bits; only its hash is stored
    with database() as db:
        saved = get_ticket(
            db, save_ticket(db, ticket.text, ticket.language, r, access_hash=token_hash(code))
        )
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
    first_help = show_first_help(Decision(auto_send=saved.auto_send, reasons=saved.reasons))
    shown = saved.auto_send or first_help
    return TicketOut(
        ticket_id=saved.id,
        category=saved.category,
        priority=saved.priority,
        office=saved.office,
        auto_send=saved.auto_send,
        first_help=first_help,
        reply=saved.draft if shown else None,
        sources=saved.sources if shown else [],
        emergency=saved.escalate and saved.priority == "urgent",
        access_code=code,
        reasons=saved.reasons,
        top_score=saved.top_score,
        min_score=MIN_SCORE,
    )


class LookupIn(BaseModel):
    """A student checks one of their tickets (sent in the body, so the code is never logged)."""

    ticket_id: int
    code: str = Field(min_length=1, max_length=100)


class TicketStatusOut(BaseModel):
    """What the student sees later: the status and the answer, never the unchecked draft."""

    ticket_id: int
    status: Status
    office: OfficeId
    reply: str | None  # the auto-sent answer or the staff reply; None while staff work on it
    handled_at: datetime | None


class FeedbackIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    helpful: bool


NOT_FOUND = "Ticket not found."  # the same for a wrong code and an unknown number


@app.post("/api/tickets/lookup", dependencies=[Depends(check_lookup_limits)])
def lookup_ticket(body: LookupIn) -> TicketStatusOut:
    """The student's own view of a ticket: status and the answer they received."""
    with database() as db:
        found = find_for_student(db, body.ticket_id, body.code)
    if found is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    reply = {"auto_sent": found.draft, "handled": found.final_reply}.get(found.status)
    return TicketStatusOut(
        ticket_id=found.id,
        status=found.status,
        office=found.office,
        reply=reply,
        handled_at=found.handled_at,
    )


@app.post(
    "/api/tickets/{ticket_id}/feedback",
    status_code=204,
    dependencies=[Depends(check_lookup_limits)],
)
def give_feedback(ticket_id: int, body: FeedbackIn) -> None:
    """Thumbs up / down on an answer; the last choice counts."""
    with database() as db:
        saved = save_feedback(
            db, ticket_id, body.code, "helpful" if body.helpful else "not_helpful"
        )
    if not saved:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    logger.info("feedback", ticket_id=ticket_id, helpful=body.helpful)


# ---------------------------------------------------------------- staff login

# Secure cookies are only sent over https. COOKIE_SECURE=false is for plain-http local development
# (read directly, like LOG_FORMAT); production keeps the default.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"
COOKIE_NAME = "helpdesk_session"
# DEMO_MODE=true (the public demo site): a one-click demo login with sample tickets only.
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


def same_origin(request: Request) -> None:
    """CSRF guard: a change (POST, PATCH, ...) coming from another website is refused. Browsers
    send an Origin header with such requests; tools like curl send none and are not affected."""
    origin = request.headers.get("origin")
    unsafe = request.method not in ("GET", "HEAD")
    if unsafe and origin and urlparse(origin).netloc != request.headers.get("host"):
        raise HTTPException(status_code=403, detail="Request from another website refused.")


def current_staff(request: Request) -> Staff:
    """The logged-in staff member, or 401. Every staff endpoint depends on this."""
    token = request.cookies.get(COOKIE_NAME)
    with database() as db:
        staff_member = auth.staff_for_session(db, token) if token else None
    if staff_member is None:
        raise HTTPException(status_code=401, detail="Please log in.")
    return staff_member


# FastAPI's recommended form: endpoints just declare `staff_member: CurrentStaff`.
CurrentStaff = Annotated[Staff, Depends(current_staff)]

login = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(same_origin)])


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def start_session(response: Response, staff_member: Staff, db: Connection) -> None:
    """Create a session and put it in the cookie (used by the normal and the demo login)."""
    response.set_cookie(
        COOKIE_NAME,
        auth.create_session(db, staff_member.id),
        max_age=auth.SESSION_HOURS * 3600,
        httponly=True,  # page scripts cannot read it, so an XSS bug cannot steal the session
        secure=COOKIE_SECURE,
        samesite="lax",  # not sent with requests that other websites start
        path="/api",  # only the API needs it
    )


class LoginOptions(BaseModel):
    demo: bool


@login.get("/options")
def login_options() -> LoginOptions:
    """What the login page can offer (the demo button only where DEMO_MODE is on)."""
    return LoginOptions(demo=DEMO_MODE)


@login.post("/demo")
def demo_log_in(response: Response) -> Staff:
    """One click: log in as the demo staff member with a fresh queue of sample tickets."""
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found.")
    with database() as db:
        staff_member = auth.demo_account(db)
        reset_demo_tickets(db)
        start_session(response, staff_member, db)
    logger.info("demo_login")
    return staff_member


@login.post("/login")
def log_in(body: LoginIn, request: Request, response: Response) -> Staff:
    """Check email and password, start a session, set the cookie. One message for every failure,
    so nobody learns whether an email exists."""
    with database() as db:
        try:
            staff_member = auth.authenticate(db, body.email, body.password, client_ip(request))
        except auth.TooManyAttempts:
            logger.warning("login_blocked")  # no email in logs: it is personal data
            raise HTTPException(
                status_code=429, detail="Too many attempts. Try again later."
            ) from None
        if staff_member is None:
            logger.info("login_failed")
            raise HTTPException(status_code=401, detail="Wrong email or password.")
        start_session(response, staff_member, db)
    logger.info("login", staff_id=staff_member.id)
    return staff_member


@login.post("/logout")
def log_out(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with database() as db:
            auth.end_session(db, token)
    response.delete_cookie(COOKIE_NAME, path="/api")
    return {"status": "logged out"}


@login.get("/me")
def me(staff_member: CurrentStaff) -> Staff:
    return staff_member


app.include_router(login)


# ---------------------------------------------------------------- staff console

# Every staff endpoint needs a logged-in staff member and refuses other websites. A router (not a
# separate app) keeps these endpoints in the same OpenAPI schema the frontend types come from.
staff = APIRouter(prefix="/api/staff", tags=["staff"], dependencies=[Depends(same_origin)])


class ReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)


class OfficeIn(BaseModel):
    office: OfficeId


def visible(ticket: StoredTicket | None, staff_member: Staff) -> StoredTicket:
    """The ticket if this staff member may see it, else 404. Staff see their own office's tickets,
    admins every office. 404 (not 403) also hides that another office's ticket exists."""
    if (
        ticket is None
        or ticket.demo != staff_member.demo  # the demo and the real world never mix
        or (staff_member.role != "admin" and ticket.office != staff_member.office)
    ):
        raise HTTPException(status_code=404, detail="No ticket with this number.")
    return ticket


def reread(db: Connection, ticket_id: int) -> StoredTicket:
    """The ticket again after a change (it existed a moment ago; checked so the type is exact)."""
    ticket = get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="No ticket with this number.")
    return ticket


@staff.get("/tickets")
def staff_list(staff_member: CurrentStaff, status: Status = "open") -> list[StoredTicket]:
    """The review queue: urgent first, then oldest first; staff see only their office."""
    with database() as db:
        office = None if staff_member.role == "admin" else staff_member.office
        return list_tickets(db, status, office, demo=staff_member.demo)


@staff.get("/insights")
def staff_insights(staff_member: CurrentStaff) -> Insights:
    """Statistics for the Insights page, with the same scope as the queue (own office; admin all)."""
    with database() as db:
        office = None if staff_member.role == "admin" else staff_member.office
        tickets = [
            ticket
            for status in get_args(Status)
            for ticket in list_tickets(db, status, office, demo=staff_member.demo)
        ]
    return summarize(tickets, datetime.now(UTC))


@staff.get("/tickets/{ticket_id}")
def staff_get(ticket_id: int, staff_member: CurrentStaff) -> StoredTicket:
    with database() as db:
        return visible(get_ticket(db, ticket_id), staff_member)


@staff.post("/tickets/{ticket_id}/reply")
def staff_reply(ticket_id: int, body: ReplyIn, staff_member: CurrentStaff) -> StoredTicket:
    """Send the staff reply and close the ticket. 409 if someone already handled it."""
    with database() as db:
        visible(get_ticket(db, ticket_id), staff_member)
        if not mark_handled(db, ticket_id, body.reply.strip()):  # atomic: only one sender wins
            raise HTTPException(status_code=409, detail="This ticket is already handled.")
        logger.info(
            "staff_reply",
            ticket_id=ticket_id,
            staff_id=staff_member.id,
            reply_length=len(body.reply.strip()),
        )
        return reread(db, ticket_id)


@staff.patch("/tickets/{ticket_id}")
def staff_reassign(ticket_id: int, body: OfficeIn, staff_member: CurrentStaff) -> StoredTicket:
    """Move the ticket to another office (it then leaves this staff member's queue)."""
    with database() as db:
        visible(get_ticket(db, ticket_id), staff_member)
        reassign(db, ticket_id, body.office)
        logger.info(
            "staff_reassign", ticket_id=ticket_id, staff_id=staff_member.id, office=body.office
        )
        return reread(db, ticket_id)


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
