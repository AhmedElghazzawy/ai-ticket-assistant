"""The staff console: the review queue, one ticket, reply, reassign, and the Insights page.

Every endpoint needs a logged-in staff member and refuses other websites. A router (not a separate
app) keeps these endpoints in the same OpenAPI schema the frontend types come from.
"""

from datetime import UTC, datetime
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from helpdesk.api.deps import CurrentStaff, ServicesDep
from helpdesk.api.security import same_origin
from helpdesk.auth import Staff
from helpdesk.core.logs import get_logger
from helpdesk.domain.offices import OfficeId
from helpdesk.insights import Insights, summarize
from helpdesk.storage.db import Connection
from helpdesk.storage.tickets import (
    Status,
    StoredTicket,
    get_ticket,
    list_tickets,
    mark_handled,
    reassign,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/staff", tags=["staff"], dependencies=[Depends(same_origin)])


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


def office_scope(staff_member: Staff) -> OfficeId | None:
    """Staff see their own office; admins see every office (None)."""
    return None if staff_member.role == "admin" else staff_member.office


@router.get("/tickets")
def staff_list(
    staff_member: CurrentStaff, services: ServicesDep, status: Status = "open"
) -> list[StoredTicket]:
    """The review queue: urgent first, then oldest first; staff see only their office."""
    with services.pool.connection() as db:
        return list_tickets(db, status, office_scope(staff_member), demo=staff_member.demo)


@router.get("/insights")
def staff_insights(staff_member: CurrentStaff, services: ServicesDep) -> Insights:
    """Statistics for the Insights page, with the same scope as the queue (own office; admin all)."""
    with services.pool.connection() as db:
        tickets = [
            ticket
            for status in get_args(Status)
            for ticket in list_tickets(
                db, status, office_scope(staff_member), demo=staff_member.demo
            )
        ]
    return summarize(tickets, datetime.now(UTC))


@router.get("/tickets/{ticket_id}")
def staff_get(ticket_id: int, staff_member: CurrentStaff, services: ServicesDep) -> StoredTicket:
    with services.pool.connection() as db:
        return visible(get_ticket(db, ticket_id), staff_member)


@router.post("/tickets/{ticket_id}/reply")
def staff_reply(
    ticket_id: int, body: ReplyIn, staff_member: CurrentStaff, services: ServicesDep
) -> StoredTicket:
    """Send the staff reply and close the ticket. 409 if someone already handled it."""
    with services.pool.connection() as db:
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


@router.patch("/tickets/{ticket_id}")
def staff_reassign(
    ticket_id: int, body: OfficeIn, staff_member: CurrentStaff, services: ServicesDep
) -> StoredTicket:
    """Move the ticket to another office (it then leaves this staff member's queue)."""
    with services.pool.connection() as db:
        visible(get_ticket(db, ticket_id), staff_member)
        reassign(db, ticket_id, body.office)
        logger.info(
            "staff_reassign", ticket_id=ticket_id, staff_id=staff_member.id, office=body.office
        )
        return reread(db, ticket_id)
