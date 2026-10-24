"""Hand-made model answers and pipeline results shared by the tests (no Gemini calls)."""

from pydantic import BaseModel

from helpdesk.ai.provider import Output, Thinking
from helpdesk.domain.decision import Decision, SimpleReason
from helpdesk.domain.outputs import Answer, Classification
from helpdesk.domain.tickets import Priority
from helpdesk.pipeline import TicketResult
from helpdesk.retrieval.knowledge_base import Chunk

CHUNK = Chunk(
    id="harc_ucretler.tr#5",
    doc="harc_ucretler",
    language="tr",
    title="Katkı Payı ve İadeler",
    source="Öğrenci İşleri SSS",
    url="https://bilecik.edu.tr/ogrenciisleri/Icerik/HARc_isLEMLERi",
    text="Kayıt sildirince iade\nGeri ödenmez.",
)


def fake_result(
    auto_send: bool,
    escalate: bool = False,
    priority: Priority = "low",
    forward_reason: SimpleReason | None = None,
) -> TicketResult:
    """A hand-made pipeline result. Forwarded results default to the reason "escalation"."""
    reason = forward_reason or SimpleReason(code="escalation")
    return TicketResult(
        classification=Classification(
            reason="test", category="billing", priority=priority, escalate=escalate
        ),
        hits=[(0.8, CHUNK)],
        answer=Answer(
            evidence="Geri ödenmez.", covered=True, reply="SECRET DRAFT", sources=[CHUNK.id]
        ),
        decision=Decision(auto_send=auto_send, reasons=[] if auto_send else [reason]),
    )


class FakeLLM:
    """An LLMProvider that returns prepared answers (one per schema) and records every call."""

    model = "fake-model"

    def __init__(self, *answers: BaseModel) -> None:
        self.answers = {type(answer): answer for answer in answers}
        self.calls: list[dict[str, object]] = []

    def generate_json(
        self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
    ) -> Output:
        self.calls.append(
            {"stage": stage, "system": system, "contents": contents, "thinking": thinking}
        )
        return schema.model_validate(self.answers[schema].model_dump())
