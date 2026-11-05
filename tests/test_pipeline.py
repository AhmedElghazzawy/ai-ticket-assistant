"""Tests for the whole pipeline with every AI call faked (no Gemini calls, no database)."""

import threading
from contextlib import AbstractContextManager

import pytest
import structlog
from fakes import CHUNK, FakeLLM
from pydantic import BaseModel

from helpdesk import pipeline
from helpdesk.ai.provider import Output, Thinking
from helpdesk.domain.outputs import Answer, Classification
from helpdesk.storage.db import Connection


def no_database() -> AbstractContextManager[Connection]:
    raise AssertionError("search is faked: the pipeline itself never opens a connection")


LABELS = Classification(reason="fee question", category="billing", priority="low", escalate=False)
ANSWER = Answer(
    evidence="Geri ödenmez.", covered=True, reply="Ödenmez.", sources=[CHUNK.id], general_help=""
)


class MeetingLLM(FakeLLM):
    """Each call waits until the other call has started too: run one after the other, they never meet."""

    def __init__(self, *answers: BaseModel) -> None:
        super().__init__(*answers)
        self.meeting = threading.Barrier(2, timeout=2)

    def generate_json(
        self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
    ) -> Output:
        self.meeting.wait()  # BrokenBarrierError after 2 s if the other call never starts
        return super().generate_json(stage, system, contents, schema, thinking)


@pytest.fixture(autouse=True)
def fake_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "search", lambda *_args, **_kwargs: [(0.8, CHUNK)])


def test_classifier_and_answer_run_at_the_same_time() -> None:
    # The answer does not need the labels, so the student waits for the slower call, not both.
    llm = MeetingLLM(LABELS, ANSWER)
    result = pipeline.process_ticket("Harç iade edilir mi?", "tr", no_database, llm)
    assert result.classification == LABELS
    assert result.answer == ANSWER


def test_a_failed_classifier_call_fails_the_ticket() -> None:
    class BrokenClassifier(FakeLLM):
        def generate_json(
            self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
        ) -> Output:
            if schema is Classification:
                raise TimeoutError("Gemini is busy")
            return super().generate_json(stage, system, contents, schema, thinking)

    with pytest.raises(TimeoutError):  # the API turns this into "not available right now"
        pipeline.process_ticket("Harç?", "tr", no_database, BrokenClassifier(LABELS, ANSWER))


def test_the_classifier_logs_keep_the_request_id() -> None:
    # The classifier runs in another thread; its gemini_call log must still name the request.
    seen: list[object] = []

    class RecordingLLM(FakeLLM):
        def generate_json(
            self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
        ) -> Output:
            seen.append(structlog.contextvars.get_contextvars().get("request_id"))
            return super().generate_json(stage, system, contents, schema, thinking)

    structlog.contextvars.bind_contextvars(request_id="req-1")
    try:
        pipeline.process_ticket("Harç?", "tr", no_database, RecordingLLM(LABELS, ANSWER))
    finally:
        structlog.contextvars.clear_contextvars()
    assert seen == ["req-1", "req-1"]  # the classifier and the answer call
