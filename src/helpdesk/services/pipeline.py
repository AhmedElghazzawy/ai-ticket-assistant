"""The whole assistant for one ticket: classify | search -> grounded answer, then decide."""

import contextvars
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from helpdesk.ai.answer import draft_answer
from helpdesk.ai.classifier import classify
from helpdesk.ai.provider import LLMProvider
from helpdesk.domain.decision import decide
from helpdesk.domain.records import TicketResult
from helpdesk.retrieval.search import search
from helpdesk.storage.db import Database

# One ticket through the whole assistant: (text, language, database) -> result. The app binds the
# model (process_ticket with Gemini); tests pass a fake.
Pipeline = Callable[[str, str, Database], TicketResult]


def process_ticket(
    ticket: str, language: str, database: Database, llm: LLMProvider
) -> TicketResult:
    """Run every step. The draft is always made: if a human takes over, they get it as a starting point.
    The answer does not need the labels, so the classifier runs at the same time as search + answer:
    the student waits for the slower of the two model calls, not for both."""
    with ThreadPoolExecutor(max_workers=1) as worker:
        # A copy of this request's context, so the classifier's logs keep the request_id.
        labels = worker.submit(contextvars.copy_context().run, classify, ticket, llm)
        hits = search(ticket, database, language=language)
        answer = draft_answer(ticket, [chunk for _, chunk in hits], language, llm)
        classification = labels.result()  # re-raises the classifier's error, if it failed
    decision = decide(
        classification, hits[0][0], answer, {chunk.id: chunk.text for _, chunk in hits}
    )
    return TicketResult(classification=classification, hits=hits, answer=answer, decision=decision)
