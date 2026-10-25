"""The whole assistant for one ticket: classify -> search -> grounded answer -> decide."""

from pydantic import BaseModel

from helpdesk.ai.answer import draft_answer
from helpdesk.ai.classifier import classify
from helpdesk.ai.provider import LLMProvider
from helpdesk.domain.decision import Decision, decide
from helpdesk.domain.outputs import Answer, Classification
from helpdesk.retrieval.knowledge_base import Chunk
from helpdesk.retrieval.search import search
from helpdesk.storage.db import Database


class TicketResult(BaseModel):
    """Everything the assistant produced for one ticket, so staff can see how it decided."""

    classification: Classification
    hits: list[tuple[float, Chunk]]  # the retrieved rules with their similarity scores
    answer: Answer
    decision: Decision


def process_ticket(
    ticket: str, language: str, database: Database, llm: LLMProvider
) -> TicketResult:
    """Run every step. The draft is always made: if a human takes over, they get it as a starting point."""
    classification = classify(ticket, llm)
    hits = search(ticket, database, language=language)
    answer = draft_answer(ticket, [chunk for _, chunk in hits], language, llm)
    decision = decide(
        classification, hits[0][0], answer, {chunk.id: chunk.text for _, chunk in hits}
    )
    return TicketResult(classification=classification, hits=hits, answer=answer, decision=decision)
