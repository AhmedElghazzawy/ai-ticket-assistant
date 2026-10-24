"""Decide: auto-send the grounded reply, or route the ticket to a human at the right office.

Plain code, not AI: a safety rule must be predictable and testable.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from answer import Answer
from classifier import Classification
from grounding import is_grounded
from tickets import Category

# Retrieval scores of answerable and unanswerable tickets overlap (Phase 3), so the score is only a weak
# floor; the main check is that the model found the answer in the rules (`covered`) and cited them.
MIN_SCORE = 0.65

# The real BŞEÜ offices (docs/PROJECT_BRIEF.md). IDs travel through the system; the page shows the name
# in the reader's language.
OfficeId = Literal["it", "student_affairs", "fees", "sks", "duty"]

OFFICE_OF: dict[Category, OfficeId] = {
    "account_access": "it",
    "it_support": "it",
    "registration": "student_affairs",
    "academic_records": "student_affairs",
    "billing": "fees",
    "campus_life": "sks",
    "other": "duty",
}

OFFICE_NAMES: dict[str, dict[OfficeId, str]] = {
    "tr": {
        "it": "Bilgi İşlem Daire Başkanlığı",
        "student_affairs": "Öğrenci İşleri Daire Başkanlığı",
        "fees": "Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü",
        "sks": "Sağlık, Kültür ve Spor (SKS) Daire Başkanlığı",
        "duty": "Öğrenci İşleri nöbetçi personeli",
    },
    "en": {
        "it": "IT Department (Bilgi İşlem)",
        "student_affairs": "Student Affairs (Öğrenci İşleri)",
        "fees": "Student Affairs, Fees Office (Harçlar Şube Müdürlüğü)",
        "sks": "Health, Culture and Sports Office (SKS)",
        "duty": "Student Affairs duty staff",
    },
}


class SimpleReason(BaseModel):
    """A failed check that needs no extra data."""

    code: Literal[
        "category_other", "escalation", "urgent", "not_covered", "no_citation", "ungrounded"
    ]


class WeakMatch(BaseModel):
    """The best document match was below the floor. Exact numbers: the page formats them."""

    # `code` has a default, but must be REQUIRED in the API schema, so the frontend can tell the
    # reason types apart by their code.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    code: Literal["weak_match"] = "weak_match"
    score: float
    min: float


# pydantic picks the right class by looking at `code` (a "discriminated union").
Reason = Annotated[SimpleReason | WeakMatch, Field(discriminator="code")]

ENGLISH: dict[str, str] = {
    "category_other": "category is 'other'",
    "escalation": "an escalation rule applies (a human must answer)",
    "urgent": "urgent: a human answers",
    "not_covered": "the documents do not answer the ticket",
    "no_citation": "the reply does not cite a retrieved document",
    "ungrounded": "the quoted evidence is not found in the retrieved documents",
}


def describe(reason: SimpleReason | WeakMatch) -> str:
    """One reason in plain English, for command-line output and the old staff panel."""
    if isinstance(reason, WeakMatch):
        return f"weak document match ({reason.score:.3f} < {reason.min:.3f})"
    return ENGLISH[reason.code]


# Reads a saved JSON list of reasons back into Reason objects.
REASON_LIST: TypeAdapter[list[SimpleReason | WeakMatch]] = TypeAdapter(list[Reason])


class Decision(BaseModel):
    """auto_send is True only if every check passed; otherwise `reasons` says which checks failed."""

    auto_send: bool
    reasons: list[Reason]


def decide(
    result: Classification, top_score: float, answer: Answer, retrieved: dict[str, str]
) -> Decision:
    """Auto-send only if ALL checks pass (docs/PROJECT_BRIEF.md). Every failed check is recorded as a reason.
    `retrieved` maps each retrieved rule id to its text."""
    reasons: list[SimpleReason | WeakMatch] = []
    if result.category == "other":
        reasons.append(SimpleReason(code="category_other"))
    if result.escalate:
        reasons.append(SimpleReason(code="escalation"))
    if result.priority == "urgent":  # blocked within 24 h or a safety risk: a person can act today
        reasons.append(SimpleReason(code="urgent"))
    if top_score < MIN_SCORE:
        reasons.append(WeakMatch(score=top_score, min=MIN_SCORE))
    if not answer.covered:
        reasons.append(SimpleReason(code="not_covered"))
    if not answer.sources or not set(answer.sources) <= retrieved.keys():
        reasons.append(SimpleReason(code="no_citation"))
    elif not is_grounded(
        answer.evidence, list(retrieved.values())
    ):  # e.g. a fake rule in the ticket
        reasons.append(SimpleReason(code="ungrounded"))
    return Decision(auto_send=not reasons, reasons=reasons)


# A forwarded draft never reaches the student if any of these checks failed (docs/decisions/0008).
NO_FIRST_HELP = {"escalation", "no_citation", "ungrounded", "weak_match"}


def show_first_help(decision: Decision) -> bool:
    """Forwarded, but the draft may help the student now: not escalated, a strong document match,
    and every cited rule was really retrieved. A person still answers the ticket."""
    return not decision.auto_send and not {r.code for r in decision.reasons} & NO_FIRST_HELP
