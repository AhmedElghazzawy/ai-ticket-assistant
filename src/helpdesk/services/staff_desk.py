"""The staff console's use cases: the queue, one ticket, reply, reassign, statistics, the demo.

The access rule lives here, once: staff see their own office's tickets, admins every office, and
the demo account only demo tickets. A ticket someone may not see looks exactly like a missing one.
"""

from datetime import UTC, datetime
from typing import get_args

from helpdesk.core.logs import get_logger
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.records import Status, StoredTicket, TicketEvent
from helpdesk.domain.staff import Staff
from helpdesk.services import auth
from helpdesk.services.errors import Conflict, NotFound
from helpdesk.services.insights import Insights, summarize
from helpdesk.storage import tickets as store
from helpdesk.storage.db import Connection

logger = get_logger(__name__)

NOT_FOUND = "No ticket with this number."


def office_scope(staff_member: Staff) -> OfficeId | None:
    """Staff see their own office; admins see every office (None)."""
    return None if staff_member.role == "admin" else staff_member.office


def visible_ticket(connection: Connection, staff_member: Staff, ticket_id: int) -> StoredTicket:
    """The ticket if this staff member may see it, else NotFound (also for another office's ticket,
    so its existence is not revealed)."""
    ticket = store.get_ticket(connection, ticket_id)
    if (
        ticket is None
        or ticket.demo != staff_member.demo  # the demo and the real world never mix
        or (staff_member.role != "admin" and ticket.office != staff_member.office)
    ):
        raise NotFound(NOT_FOUND)
    return ticket


def queue(connection: Connection, staff_member: Staff, status: Status) -> list[StoredTicket]:
    """The review queue: urgent first, then oldest first."""
    return store.list_tickets(
        connection, status, office_scope(staff_member), demo=staff_member.demo
    )


def insights(connection: Connection, staff_member: Staff) -> Insights:
    """Statistics with the same scope as the queue (own office; admin all)."""
    tickets = [t for status in get_args(Status) for t in queue(connection, staff_member, status)]
    return summarize(tickets, datetime.now(UTC))


def history(connection: Connection, staff_member: Staff, ticket_id: int) -> list[TicketEvent]:
    """Who did what on this ticket, oldest first (docs/decisions/0017); same access rule."""
    visible_ticket(connection, staff_member, ticket_id)
    return store.list_events(connection, ticket_id)


def reply(connection: Connection, staff_member: Staff, ticket_id: int, text: str) -> StoredTicket:
    """Send the staff reply and close the ticket. Conflict if someone already handled it."""
    visible_ticket(connection, staff_member, ticket_id)
    text = text.strip()
    if not store.mark_handled(
        connection, ticket_id, text, staff_member.id
    ):  # atomic: only one sender wins
        raise Conflict("This ticket is already handled.")
    logger.info(
        "staff_reply", ticket_id=ticket_id, staff_id=staff_member.id, reply_length=len(text)
    )
    return visible_ticket(connection, staff_member, ticket_id)


def reassign(
    connection: Connection, staff_member: Staff, ticket_id: int, office: OfficeId
) -> StoredTicket:
    """Move the ticket to another office (it then leaves this staff member's queue). Read back
    without the office check: the staff member who moved it still gets the result."""
    visible_ticket(connection, staff_member, ticket_id)
    store.reassign(connection, ticket_id, office, staff_member.id)
    logger.info("staff_reassign", ticket_id=ticket_id, staff_id=staff_member.id, office=office)
    moved = store.get_ticket(connection, ticket_id)
    if moved is None:  # it existed a moment ago; checked so the type is exact
        raise NotFound(NOT_FOUND)
    return moved


def start_demo(connection: Connection) -> Staff:
    """The demo staff member with a fresh queue of sample tickets (real tickets are never touched)."""
    staff_member = auth.demo_account(connection)
    store.reset_demo_tickets(connection)
    return staff_member
