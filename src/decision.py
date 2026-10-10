"""Decide: auto-send the grounded reply, or route the ticket to a human at the right office.

Plain code, not AI: a safety rule must be predictable and testable.
"""

from pydantic import BaseModel

from answer import Answer
from classifier import Classification

# Retrieval scores of answerable and unanswerable tickets overlap (Phase 3), so the score is only a weak
# floor; the main check is that the model found the answer in the rules (`covered`) and cited them.
MIN_SCORE = 0.65

# Where each category is routed: the real BŞEÜ offices decided in CLAUDE.md.
UNITS = {
    "tr": {"account_access": "Bilgi İşlem Daire Başkanlığı", "it_support": "Bilgi İşlem Daire Başkanlığı",
           "registration": "Öğrenci İşleri Daire Başkanlığı", "academic_records": "Öğrenci İşleri Daire Başkanlığı",
           "billing": "Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü",
           "campus_life": "Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı", "other": "Öğrenci İşleri nöbetçi personeli"},
    "en": {"account_access": "IT Department (Bilgi İşlem)", "it_support": "IT Department (Bilgi İşlem)",
           "registration": "Student Affairs (Öğrenci İşleri)", "academic_records": "Student Affairs (Öğrenci İşleri)",
           "billing": "Student Affairs, Fees Office (Harçlar Şube Müdürlüğü)",
           "campus_life": "Health, Culture and Sports Office (SKS)", "other": "Student Affairs duty staff"},
}


class Decision(BaseModel):
    """auto_send is True only if every check passed; otherwise `reasons` says which checks failed."""

    auto_send: bool
    reasons: list[str]


def decide(result: Classification, top_score: float, answer: Answer, retrieved_ids: set[str]) -> Decision:
    """Auto-send only if ALL checks pass (CLAUDE.md). Every failed check is recorded as a reason."""
    reasons = []
    if result.category == "other":
        reasons.append("category is 'other'")
    if result.escalate:
        reasons.append("an escalation rule applies (a human must answer)")
    if result.priority == "urgent":  # blocked within 24 h or a safety risk: a person can act today
        reasons.append("urgent: a human answers")
    if top_score < MIN_SCORE:
        reasons.append(f"weak document match ({top_score:.2f} < {MIN_SCORE})")
    if not answer.covered:
        reasons.append("the documents do not answer the ticket")
    if not answer.sources or not set(answer.sources) <= retrieved_ids:
        reasons.append("the reply does not cite a retrieved document")
    return Decision(auto_send=not reasons, reasons=reasons)
