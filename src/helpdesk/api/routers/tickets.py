"""The student's endpoints: send a ticket, check its status later, say if the answer helped."""

import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from helpdesk.api.deps import ServicesDep
from helpdesk.api.security import client_ip
from helpdesk.core.logs import get_logger
from helpdesk.domain.decision import MIN_SCORE, Decision, Reason, show_first_help
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.tickets import Category, Priority
from helpdesk.storage.db import token_hash
from helpdesk.storage.tickets import (
    Status,
    StoredSource,
    count_tickets_since,
    find_for_student,
    get_ticket,
    save_feedback,
    save_ticket,
)

logger = get_logger(__name__)


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


def check_ticket_limits(request: Request, services: ServicesDep) -> None:
    """Runs BEFORE the pipeline, so a refused request never costs a Gemini call."""
    cap = services.settings.daily_ticket_cap
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with services.pool.connection() as db:
        if count_tickets_since(db, midnight) >= cap:
            logger.warning("daily_cap_reached", cap=cap)
            raise HTTPException(
                status_code=429, detail="The assistant is busy today. Try tomorrow."
            )
    if not services.ticket_limiter.allow(client_ip(request, services.settings.client_ip_header)):
        logger.info("visitor_rate_limited")  # never the address itself
        raise HTTPException(status_code=429, detail="Too many questions. Please wait a minute.")


def check_lookup_limits(request: Request, services: ServicesDep) -> None:
    if not services.lookup_limiter.allow(client_ip(request, services.settings.client_ip_header)):
        logger.info("lookup_rate_limited")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")


router = APIRouter(prefix="/api/tickets")


@router.post("", dependencies=[Depends(check_ticket_limits)])
def create_ticket(ticket: TicketIn, services: ServicesDep) -> TicketOut:
    """Run the whole pipeline for one student message."""
    try:
        r = services.pipeline(ticket.text, ticket.language, services.database())
    except Exception as error:  # show students a short message only
        # Only the error TYPE: an error message can contain the model's output, which may echo
        # the student's words (personal data never goes into logs).
        logger.error("pipeline_failed", error_type=type(error).__name__)
        raise HTTPException(
            status_code=503, detail="The assistant is not available right now."
        ) from error
    code = secrets.token_urlsafe(16)  # 128 random bits; only its hash is stored
    with services.pool.connection() as db:
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


@router.post("/lookup", dependencies=[Depends(check_lookup_limits)])
def lookup_ticket(body: LookupIn, services: ServicesDep) -> TicketStatusOut:
    """The student's own view of a ticket: status and the answer they received."""
    with services.pool.connection() as db:
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


@router.post("/{ticket_id}/feedback", status_code=204, dependencies=[Depends(check_lookup_limits)])
def give_feedback(ticket_id: int, body: FeedbackIn, services: ServicesDep) -> None:
    """Thumbs up / down on an answer; the last choice counts."""
    with services.pool.connection() as db:
        saved = save_feedback(
            db, ticket_id, body.code, "helpful" if body.helpful else "not_helpful"
        )
    if not saved:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    logger.info("feedback", ticket_id=ticket_id, helpful=body.helpful)
