"""The student's use cases: send a ticket, check it later, ask for a person, say if it helped.

Students have no account: every later action needs the ticket's secret code, shown once
(docs/decisions/0009). What the student may see is decided here, from the SAVED ticket, so students
and staff always see the same data and an unchecked draft never leaves the server.
"""

import secrets
from datetime import datetime

from pydantic import BaseModel

from helpdesk.core.logs import get_logger
from helpdesk.domain.decision import (
    MIN_SCORE,
    Decision,
    Reason,
    show_first_help,
    show_general_help,
)
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.records import Feedback, Status, StoredSource, StoredTicket
from helpdesk.domain.tickets import Category, Language, Priority
from helpdesk.services.errors import AssistantUnavailable, Conflict, NotFound
from helpdesk.services.pipeline import Pipeline
from helpdesk.storage import tickets as store
from helpdesk.storage.db import Connection, Database, token_hash

logger = get_logger(__name__)

NOT_FOUND = "Ticket not found."  # the same for a wrong code and an unknown number


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
    # Labeled general advice for what the rules do not answer; None when escalated (a person answers)
    # or when the ticket planted a fake rule (decision.show_general_help).
    general_help: str | None
    emergency: bool  # show the 112 line (urgent and escalated)
    access_code: str  # shown ONCE: with it, only this student can see the status and give feedback
    # "Nasıl karar verildi?": the checks behind the decision (never the draft or the model's text)
    reasons: list[Reason]  # failed checks; empty when the answer was sent automatically
    top_score: float  # the best document match
    min_score: float  # the threshold it is compared with


class TicketStatusOut(BaseModel):
    """What the student sees later: the status and the answer, never the unchecked draft."""

    ticket_id: int
    status: Status
    office: OfficeId
    # The staff reply, else the automatic answer the student already got (also after they asked for
    # a person); None while staff work on a forwarded ticket.
    reply: str | None
    handled_at: datetime | None
    human_requested: bool  # the student sent the automatic answer on to a person


def daily_cap_reached(connection: Connection, cap: int, midnight: datetime) -> bool:
    """The whole system's daily limit of new tickets (a cost guard for the paid model)."""
    reached = store.count_tickets_since(connection, midnight) >= cap
    if reached:
        logger.warning("daily_cap_reached", cap=cap)
    return reached


def submit_ticket(text: str, language: Language, run: Pipeline, database: Database) -> TicketOut:
    """Run the assistant on one message, save the result with a new secret code, and return what
    the student may see."""
    try:
        result = run(text, language, database)
    except Exception as error:
        # Only the error TYPE: an error message can contain the model's output, which may echo
        # the student's words (personal data never goes into logs).
        logger.error("pipeline_failed", error_type=type(error).__name__)
        raise AssistantUnavailable("The assistant is not available right now.") from error
    code = secrets.token_urlsafe(16)  # 128 random bits; only its hash is stored
    with database() as db:
        saved = store.get_ticket(
            db, store.save_ticket(db, text, language, result, access_hash=token_hash(code))
        )
    if saved is None:  # cannot happen right after saving; checked so the type is exact
        raise RuntimeError("The ticket could not be saved.")
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
    return answer_view(saved, code)


def answer_view(saved: StoredTicket, code: str) -> TicketOut:
    """The first answer: the reply only if it was sent or is safe first help (ADR 0008, 0013)."""
    decision = Decision(auto_send=saved.auto_send, reasons=saved.reasons)
    first_help = show_first_help(decision)
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
        general_help=(saved.general_help or None) if show_general_help(decision) else None,
        emergency=saved.escalate and saved.priority == "urgent",
        access_code=code,
        reasons=saved.reasons,
        top_score=saved.top_score,
        min_score=MIN_SCORE,
    )


def status_view(found: StoredTicket) -> TicketStatusOut:
    """The later view: the staff reply, else the automatic answer already shown; a forwarded draft
    never."""
    if found.status == "handled":
        reply = found.final_reply
    else:
        reply = found.draft if found.auto_send else None
    return TicketStatusOut(
        ticket_id=found.id,
        status=found.status,
        office=found.office,
        reply=reply,
        handled_at=found.handled_at,
        human_requested=found.human_requested_at is not None,
    )


def lookup(connection: Connection, ticket_id: int, code: str) -> TicketStatusOut:
    found = store.find_for_student(connection, ticket_id, code)
    if found is None:
        raise NotFound(NOT_FOUND)
    return status_view(found)


def ask_for_a_person(connection: Connection, ticket_id: int, code: str) -> TicketStatusOut:
    """The "Still need help?" button: a person in the ticket's office takes over the automatic answer
    (docs/decisions/0016). Asking twice, or on a forwarded ticket, changes nothing; a ticket staff
    already answered is not reopened (that could loop staff without end)."""
    status = store.request_human(connection, ticket_id, code)
    found = store.find_for_student(connection, ticket_id, code) if status else None
    if found is None:
        raise NotFound(NOT_FOUND)
    if status == "handled":
        raise Conflict("Staff already answered this ticket.")
    logger.info("human_requested", ticket_id=ticket_id)  # never the text or the code
    return status_view(found)


def give_feedback(connection: Connection, ticket_id: int, code: str, helpful: bool) -> None:
    """Thumbs up / down on an answer; the last choice counts."""
    feedback: Feedback = "helpful" if helpful else "not_helpful"
    if not store.save_feedback(connection, ticket_id, code, feedback):
        raise NotFound(NOT_FOUND)
    logger.info("feedback", ticket_id=ticket_id, helpful=helpful)
