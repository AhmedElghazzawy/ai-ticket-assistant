"""The staff console's endpoints: HTTP only; the rules are in services/staff_desk.py.

Every endpoint needs a logged-in staff member and refuses other websites. A router (not a separate
app) keeps these endpoints in the same OpenAPI schema the frontend types come from.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from helpdesk.api.deps import CurrentStaff, ServicesDep
from helpdesk.api.security import same_origin
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.records import Status, StoredTicket
from helpdesk.services import staff_desk
from helpdesk.services.insights import Insights

router = APIRouter(prefix="/api/staff", tags=["staff"], dependencies=[Depends(same_origin)])


class ReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=5000)


class OfficeIn(BaseModel):
    office: OfficeId


@router.get("/tickets")
def staff_list(
    staff_member: CurrentStaff, services: ServicesDep, status: Status = "open"
) -> list[StoredTicket]:
    """The review queue: urgent first, then oldest first; staff see only their office."""
    with services.pool.connection() as db:
        return staff_desk.queue(db, staff_member, status)


@router.get("/insights")
def staff_insights(staff_member: CurrentStaff, services: ServicesDep) -> Insights:
    """Statistics for the Insights page, with the same scope as the queue (own office; admin all)."""
    with services.pool.connection() as db:
        return staff_desk.insights(db, staff_member)


@router.get("/tickets/{ticket_id}")
def staff_get(ticket_id: int, staff_member: CurrentStaff, services: ServicesDep) -> StoredTicket:
    with services.pool.connection() as db:
        return staff_desk.visible_ticket(db, staff_member, ticket_id)


@router.post("/tickets/{ticket_id}/reply")
def staff_reply(
    ticket_id: int, body: ReplyIn, staff_member: CurrentStaff, services: ServicesDep
) -> StoredTicket:
    """Send the staff reply and close the ticket. 409 if someone already handled it."""
    with services.pool.connection() as db:
        return staff_desk.reply(db, staff_member, ticket_id, body.reply)


@router.patch("/tickets/{ticket_id}")
def staff_reassign(
    ticket_id: int, body: OfficeIn, staff_member: CurrentStaff, services: ServicesDep
) -> StoredTicket:
    """Move the ticket to another office (it then leaves this staff member's queue)."""
    with services.pool.connection() as db:
        return staff_desk.reassign(db, staff_member, ticket_id, body.office)
