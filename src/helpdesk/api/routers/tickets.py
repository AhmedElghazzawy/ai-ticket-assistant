"""The student's endpoints: HTTP only. Input checks and rate limits here; the rules are in
services/student_tickets.py."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from helpdesk.api.deps import ServicesDep
from helpdesk.api.security import client_ip
from helpdesk.core.logs import get_logger
from helpdesk.services import student_tickets
from helpdesk.services.student_tickets import TicketOut, TicketStatusOut

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


class LookupIn(BaseModel):
    """A student checks one of their tickets (sent in the body, so the code is never logged)."""

    ticket_id: int
    code: str = Field(min_length=1, max_length=100)


class CodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)


class FeedbackIn(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    helpful: bool


def check_ticket_limits(request: Request, services: ServicesDep) -> None:
    """Runs BEFORE the pipeline, so a refused request never costs a Gemini call."""
    cap = services.settings.daily_ticket_cap
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with services.pool.connection() as db:
        if student_tickets.daily_cap_reached(db, cap, midnight):
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
    return student_tickets.submit_ticket(
        ticket.text, ticket.language, services.pipeline, services.database()
    )


@router.post("/lookup", dependencies=[Depends(check_lookup_limits)])
def lookup_ticket(body: LookupIn, services: ServicesDep) -> TicketStatusOut:
    """The student's own view of a ticket: status and the answer they received."""
    with services.pool.connection() as db:
        return student_tickets.lookup(db, body.ticket_id, body.code)


@router.post(
    "/{ticket_id}/human",
    dependencies=[Depends(check_lookup_limits)],
    responses={409: {"description": "Staff already answered this ticket."}},
)
def ask_for_a_person(ticket_id: int, body: CodeIn, services: ServicesDep) -> TicketStatusOut:
    """The student's "Still need help?" button: the automatic answer did not solve it, so a person
    in the ticket's office takes over (docs/decisions/0016). Asking twice, or on a forwarded ticket,
    changes nothing."""
    with services.pool.connection() as db:
        return student_tickets.ask_for_a_person(db, ticket_id, body.code)


@router.post("/{ticket_id}/feedback", status_code=204, dependencies=[Depends(check_lookup_limits)])
def give_feedback(ticket_id: int, body: FeedbackIn, services: ServicesDep) -> None:
    """Thumbs up / down on an answer; the last choice counts."""
    with services.pool.connection() as db:
        student_tickets.give_feedback(db, ticket_id, body.code, body.helpful)
