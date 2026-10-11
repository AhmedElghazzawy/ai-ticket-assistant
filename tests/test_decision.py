"""Tests for the auto-send rule: no AI calls, only hand-made inputs."""

from typing import get_args

from answer import Answer
from classifier import Classification
from decision import MIN_SCORE, OFFICE_NAMES, OFFICE_OF, WeakMatch, decide
from tickets import Category

RETRIEVED = {"sinavlar.en#4", "sinavlar.en#1"}
GOOD_ANSWER = Answer(evidence="a rule", covered=True, reply="a reply", sources=["sinavlar.en#4"])


def labels(category: Category = "academic_records", escalate: bool = False) -> Classification:
    """A hand-made classification for the tests."""
    return Classification(reason="test", category=category, priority="medium", escalate=escalate)


def test_all_checks_pass_means_auto_send() -> None:
    decision = decide(labels(), 0.80, GOOD_ANSWER, RETRIEVED)
    assert decision.auto_send
    assert decision.reasons == []


def test_category_other_is_never_auto_sent() -> None:
    assert not decide(labels(category="other"), 0.80, GOOD_ANSWER, RETRIEVED).auto_send


def test_escalated_ticket_is_never_auto_sent() -> None:
    assert not decide(labels(escalate=True), 0.80, GOOD_ANSWER, RETRIEVED).auto_send


def test_weak_document_match_is_not_auto_sent() -> None:
    assert not decide(labels(), MIN_SCORE - 0.01, GOOD_ANSWER, RETRIEVED).auto_send


def test_uncovered_answer_is_not_auto_sent() -> None:
    uncovered = Answer(evidence="", covered=False, reply="we will forward it", sources=[])
    assert not decide(labels(), 0.80, uncovered, RETRIEVED).auto_send


def test_citing_a_document_that_was_not_retrieved_is_not_auto_sent() -> None:
    invented = Answer(evidence="a rule", covered=True, reply="a reply", sources=["staj.en#2"])
    assert not decide(labels(), 0.80, invented, RETRIEVED).auto_send


def test_every_failed_check_is_reported() -> None:
    decision = decide(labels(category="other", escalate=True), 0.10, GOOD_ANSWER, RETRIEVED)
    assert [reason.code for reason in decision.reasons] == [
        "category_other",
        "escalation",
        "weak_match",
    ]


def test_weak_match_keeps_the_exact_score() -> None:
    # Bug found in the staff console: 0.6497 was shown as "0.65 < 0.65". The reason now carries
    # the exact numbers and the page formats them.
    decision = decide(labels(), 0.6497, GOOD_ANSWER, RETRIEVED)
    assert decision.reasons == [WeakMatch(score=0.6497, min=MIN_SCORE)]


def test_every_category_is_routed_to_an_office() -> None:
    assert set(OFFICE_OF) == set(get_args(Category))


def test_every_office_has_a_name_in_both_languages() -> None:
    for language in ("tr", "en"):
        assert set(OFFICE_NAMES[language]) == set(OFFICE_OF.values())


def test_urgent_ticket_is_never_auto_sent() -> None:
    urgent = Classification(
        reason="test", category="account_access", priority="urgent", escalate=False
    )
    assert not decide(urgent, 0.80, GOOD_ANSWER, RETRIEVED).auto_send
