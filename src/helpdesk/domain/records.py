"""What the assistant produced for one ticket, and what a saved ticket looks like.

Plain data, shared by every layer: the pipeline builds a TicketResult, storage saves it as a row and
reads it back as a StoredTicket, and the staff API returns StoredTicket as it is.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from helpdesk.domain.decision import Decision, Reason
from helpdesk.domain.knowledge import Chunk
from helpdesk.domain.offices import OfficeId
from helpdesk.domain.outputs import Answer, Classification
from helpdesk.domain.tickets import Category, Language, Priority


class TicketResult(BaseModel):
    """Everything the assistant produced for one ticket, so staff can see how it decided."""

    classification: Classification
    hits: list[tuple[float, Chunk]]  # the retrieved rules with their similarity scores
    answer: Answer
    decision: Decision


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
    general_help: str  # labeled general advice, not from the rules ("" in older rows)
    status: Status
    final_reply: str | None
    handled_at: datetime | None
    demo: bool  # a sample ticket for the demo: never mixed with real visitors' tickets
    feedback: Feedback | None = None  # the student's thumbs up / down, if they gave one
    # When the student sent the automatic answer on to a person; None if they never asked.
    human_requested_at: datetime | None = None
