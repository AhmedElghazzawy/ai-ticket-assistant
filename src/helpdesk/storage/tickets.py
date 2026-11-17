"""The ticket table: save a processed ticket, the staff queue, the student's own view, the demo queue."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from helpdesk.core.paths import DATA_DIR
from helpdesk.domain.offices import OFFICE_OF, OfficeId
from helpdesk.domain.records import (
    Feedback,
    Status,
    StoredSource,
    StoredTicket,
    TicketEvent,
    TicketResult,
)
from helpdesk.domain.tickets import Language
from helpdesk.storage.db import Connection, token_hash

# The demo queue (tools/make_demo_tickets.py builds it from the dataset and its real results).
DEMO_PATH = DATA_DIR / "demo_tickets.json"


def save_ticket(
    connection: Connection,
    text: str,
    language: Language,
    result: TicketResult,
    access_hash: str | None = None,
) -> int:
    """Store one processed ticket and return its number. Auto-sent tickets are stored too (for statistics)."""
    c, decision, answer = result.classification, result.decision, result.answer
    cited = {chunk.id: chunk for _, chunk in result.hits}
    sources = [
        StoredSource(
            id=i,
            title=cited[i].title,
            section=cited[i].section,
            source=cited[i].source,
            url=cited[i].url,
        )
        for i in answer.sources
        if i in cited  # a cited id that was never retrieved is not shown (the decision flags it)
    ]
    row = connection.execute(
        "WITH ticket AS (INSERT INTO tickets (language, text, category, priority, escalate,"
        " ai_reason, office, auto_send, reasons, top_score, draft, covered, sources, general_help,"
        " status, access_hash)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING id, created_at, office)"
        # The first history event, in the same statement: a ticket never exists without it.
        " INSERT INTO ticket_events (ticket_id, at, kind, detail)"
        " SELECT id, created_at, 'created', jsonb_build_object('to', office) FROM ticket"
        " RETURNING ticket_id AS id",
        (
            language,
            text,
            c.category,
            c.priority,
            c.escalate,
            c.reason,
            OFFICE_OF[c.category],
            decision.auto_send,
            Jsonb([reason.model_dump() for reason in decision.reasons]),
            result.hits[0][0] if result.hits else 0.0,
            answer.reply,
            answer.covered,
            Jsonb([source.model_dump() for source in sources]),
            answer.general_help,
            "auto_sent" if decision.auto_send else "open",
            access_hash,
        ),
    ).fetchone()
    if row is None:  # RETURNING always gives the new row; checked so the type is a plain int
        raise RuntimeError("Postgres did not return the new ticket number.")
    return int(row["id"])


PRIORITY_ORDER = (
    "CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
)


def count_tickets_since(connection: Connection, since: datetime) -> int:
    """How many real (not demo) tickets arrived since this time (for the daily cap)."""
    row = connection.execute(
        "SELECT count(*) AS n FROM tickets WHERE NOT demo AND created_at >= %s", (since,)
    ).fetchone()
    return int(row["n"]) if row else 0


def list_tickets(
    connection: Connection, status: Status, office: OfficeId | None = None, demo: bool = False
) -> list[StoredTicket]:
    """Tickets with this status (only this office's, if given; real or demo, never both),
    most urgent first, then the longest wait first."""
    rows = connection.execute(
        "SELECT * FROM tickets"
        " WHERE status = %s AND (%s::text IS NULL OR office = %s) AND demo = %s"
        f" ORDER BY {PRIORITY_ORDER}, created_at, id",  # our own constant, not user input
        (status, office, office, demo),
    ).fetchall()
    return [StoredTicket.model_validate(row) for row in rows]


def get_ticket(connection: Connection, ticket_id: int) -> StoredTicket | None:
    """One ticket, or None if the number does not exist."""
    row = connection.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    return StoredTicket.model_validate(row) if row else None


def find_for_student(connection: Connection, ticket_id: int, code: str) -> StoredTicket | None:
    """The ticket, only with its secret code. A wrong code and an unknown number both give None."""
    row = connection.execute(
        "SELECT * FROM tickets WHERE id = %s AND access_hash = %s AND NOT demo",
        (ticket_id, token_hash(code)),
    ).fetchone()
    return StoredTicket.model_validate(row) if row else None


def save_feedback(connection: Connection, ticket_id: int, code: str, feedback: Feedback) -> bool:
    """The student's thumbs up / down (the last choice counts). False if number or code is wrong."""
    row = connection.execute(
        "UPDATE tickets SET feedback = %s, feedback_at = now()"
        " WHERE id = %s AND access_hash = %s AND NOT demo RETURNING id",
        (feedback, ticket_id, token_hash(code)),
    ).fetchone()
    return row is not None


def request_human(connection: Connection, ticket_id: int, code: str) -> Status | None:
    """The student is not helped by the automatic answer: put the ticket in its office's queue.
    Only an auto-sent ticket moves; an open one is already with a person and a handled one already
    has the staff reply, so those stay as they are. Returns the status afterwards, or None if the
    number or code is wrong."""
    moved = connection.execute(
        "WITH moved AS (UPDATE tickets SET status = 'open', human_requested_at = now()"
        " WHERE id = %s AND access_hash = %s AND NOT demo AND status = 'auto_sent'"
        " RETURNING id, human_requested_at)"
        " INSERT INTO ticket_events (ticket_id, at, kind)"
        " SELECT id, human_requested_at, 'human_requested' FROM moved RETURNING ticket_id",
        (ticket_id, token_hash(code)),
    ).fetchone()
    if moved is not None:
        return "open"
    found = find_for_student(connection, ticket_id, code)
    return found.status if found else None


def mark_handled(connection: Connection, ticket_id: int, final_reply: str, staff_id: int) -> bool:
    """Staff finished this ticket. Returns False if it was not open any more. One atomic statement:
    if two staff members send at the same moment, exactly one of them wins, and only the winner's
    reply is in the history."""
    row = connection.execute(
        "WITH handled AS (UPDATE tickets SET status = 'handled', final_reply = %s, handled_at = now()"
        " WHERE id = %s AND status = 'open' RETURNING id, handled_at)"
        " INSERT INTO ticket_events (ticket_id, at, kind, staff_id)"
        " SELECT id, handled_at, 'replied', %s FROM handled RETURNING ticket_id",
        (final_reply, ticket_id, staff_id),
    ).fetchone()
    return row is not None


def reassign(connection: Connection, ticket_id: int, office: OfficeId, staff_id: int) -> None:
    """Staff moved the ticket to another office (moving it to the office it is in records nothing).
    Every part of one statement sees the same snapshot, so `old` is the office before the move."""
    connection.execute(
        "WITH old AS (SELECT id, office FROM tickets WHERE id = %(id)s),"
        " moved AS (UPDATE tickets SET office = %(office)s"
        " WHERE id = %(id)s AND office <> %(office)s RETURNING id)"
        " INSERT INTO ticket_events (ticket_id, kind, staff_id, detail)"
        " SELECT id, 'reassigned', %(staff_id)s,"
        " jsonb_build_object('from', old.office, 'to', %(office)s::text)"
        " FROM moved JOIN old USING (id)",
        {"id": ticket_id, "office": office, "staff_id": staff_id},
    )


def list_events(connection: Connection, ticket_id: int) -> list[TicketEvent]:
    """The ticket's history, oldest first, with the staff member's name where staff acted."""
    rows = connection.execute(
        "SELECT e.at, e.kind, s.name AS staff_name,"
        " e.detail ->> 'from' AS from_office, e.detail ->> 'to' AS to_office"
        " FROM ticket_events e LEFT JOIN staff s ON s.id = e.staff_id"
        " WHERE e.ticket_id = %s ORDER BY e.at, e.id",
        (ticket_id,),
    ).fetchall()
    return [TicketEvent.model_validate(row) for row in rows]


def reset_demo_tickets(connection: Connection) -> int:
    """Put the demo queue back to its starting state (every demo login gets a fresh queue).
    Only demo rows are touched: real tickets are never changed."""
    samples: list[dict[str, Any]] = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    with connection.transaction():  # one transaction: the demo queue is never half-reset
        connection.execute("DELETE FROM tickets WHERE demo")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO tickets (created_at, language, text, category, priority, escalate,"
                " ai_reason, office, auto_send, reasons, top_score, draft, covered, sources,"
                " status, demo)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, %s, %s, %s, %s, %s, 'open', true)",
                [
                    (
                        now - timedelta(minutes=t["age_minutes"]),
                        t["language"],
                        t["text"],
                        t["category"],
                        t["priority"],
                        t["escalate"],
                        t["ai_reason"],
                        t["office"],
                        Jsonb(t["reasons"]),
                        t["top_score"],
                        t["draft"],
                        t["covered"],
                        Jsonb(t["sources"]),
                    )
                    for t in samples
                ],
            )
        connection.execute(  # each sample starts its history, like a real ticket
            "INSERT INTO ticket_events (ticket_id, at, kind, detail)"
            " SELECT id, created_at, 'created', jsonb_build_object('to', office)"
            " FROM tickets WHERE demo"
        )
    return len(samples)
