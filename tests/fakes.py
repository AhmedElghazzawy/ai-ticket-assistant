"""Hand-made pipeline results shared by the API and logging tests (no Gemini calls)."""

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
