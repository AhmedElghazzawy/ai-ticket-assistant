"""The ticket table: save a processed ticket, the staff queue, the student's own view, the demo queue."""

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from psycopg.types.json import Jsonb
from pydantic import BaseModel

from helpdesk.core.paths import DATA_DIR
from helpdesk.domain.decision import Reason
from helpdesk.domain.offices import OFFICE_OF, OfficeId
from helpdesk.domain.tickets import Category, Language, Priority
from helpdesk.storage.db import Connection, token_hash

if TYPE_CHECKING:  # only for the type hint, so this module does not load the AI pipeline
    from helpdesk.pipeline import TicketResult

# The demo queue (tools/make_demo_tickets.py builds it from the dataset and its real results).
DEMO_PATH = DATA_DIR / "demo_tickets.json"


Status = Literal["auto_sent", "open", "handled"]


Feedback = Literal["helpful", "not_helpful"]


class StoredSource(BaseModel):
    id: str  # e.g. "harc_ucretler.tr#5"
    title: str
    section: str
    source: str = ""  # the official source line, e.g. "Resmî olmayan kaynak: ..."; "" in older rows
    url: str


class StoredTicket(BaseModel):
    """One row, checked by pydantic: a broken row fails here, not later on the page."""

    id: int
    created_at: datetime
    language: Language
    text: str
    category: Category
    priority: Priority
    escalate: bool
    ai_reason: str
    office: OfficeId
    auto_send: bool
    reasons: list[Reason]
    top_score: float
    draft: str
    covered: bool
    sources: list[StoredSource]
    status: Status
    final_reply: str | None
    handled_at: datetime | None
    demo: bool  # a sample ticket for the demo: never mixed with real visitors' tickets
    feedback: Feedback | None = None  # the student's thumbs up / down, if they gave one


def save_ticket(
    connection: Connection,
    text: str,
    language: Language,
    result: "TicketResult",
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
        "INSERT INTO tickets (language, text, category, priority, escalate, ai_reason, office,"
        " auto_send, reasons, top_score, draft, covered, sources, status, access_hash)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
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
            "auto_sent" if decision.auto_send else "open",
            access_hash,
        ),
    ).fetchone()  # %s placeholders: psycopg sends the values separately (no SQL injection)
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


def mark_handled(connection: Connection, ticket_id: int, final_reply: str) -> bool:
    """Staff finished this ticket. Returns False if it was not open any more. One atomic UPDATE:
    if two staff members send at the same moment, exactly one of them wins."""
    row = connection.execute(
        "UPDATE tickets SET status = 'handled', final_reply = %s, handled_at = now()"
        " WHERE id = %s AND status = 'open' RETURNING id",
        (final_reply, ticket_id),
    ).fetchone()
    return row is not None


def reassign(connection: Connection, ticket_id: int, office: OfficeId) -> None:
    """Staff moved the ticket to another office."""
    connection.execute("UPDATE tickets SET office = %s WHERE id = %s", (office, ticket_id))


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
    return len(samples)
