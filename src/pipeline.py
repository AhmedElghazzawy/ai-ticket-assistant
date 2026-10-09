"""The whole assistant for one ticket: classify -> search -> grounded answer -> decide."""

from pydantic import BaseModel

from answer import Answer, draft_answer
from classifier import Classification, classify
from decision import Decision, decide
from knowledge_base import Chunk
from retrieval import search


class TicketResult(BaseModel):
    """Everything the assistant produced for one ticket, so staff can see how it decided."""

    classification: Classification
    hits: list[tuple[float, Chunk]]  # the retrieved rules with their similarity scores
    answer: Answer
    decision: Decision


def process_ticket(ticket: str, language: str, index: list) -> TicketResult:
    """Run every step. The draft is always made: if a human takes over, they get it as a starting point."""
    classification = classify(ticket)
    hits = search(ticket, index, language=language)
    answer = draft_answer(ticket, [chunk for _, chunk in hits], language)
    decision = decide(classification, hits[0][0], answer, {chunk.id for _, chunk in hits})
    return TicketResult(classification=classification, hits=hits, answer=answer, decision=decision)
