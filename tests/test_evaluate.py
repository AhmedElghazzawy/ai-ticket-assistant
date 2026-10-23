"""Tests for scoring the classifier: hand-made tickets and predictions, no AI calls."""

from typing import Any

import pytest

from evaluate import score
from stats import wilson_interval
from tickets import Ticket


def ticket(tid: str, escalate: bool = False) -> Ticket:
    return Ticket(
        id=tid,
        text="text",
        language="en",
        category="billing",
        priority="medium",
        escalate=escalate,
    )


def prediction(category: str = "billing", escalate: bool = False) -> dict[str, Any]:
    return {"reason": "r", "category": category, "priority": "medium", "escalate": escalate}


TICKETS = [ticket("a"), ticket("b"), ticket("c", escalate=True)]
PREDICTIONS = {
    "a": prediction(),
    "b": prediction(category="other"),  # wrong category
    "c": prediction(),  # needed a human, not escalated
}


def test_accuracy_comes_with_its_interval() -> None:
    result = score(TICKETS, PREDICTIONS)
    assert result["n"] == 3
    assert result["category"] == pytest.approx(2 / 3)
    assert result["category_ci"] == wilson_interval(2, 3)
    assert result["all_three"] == pytest.approx(1 / 3)
    assert result["all_three_ci"] == wilson_interval(1, 3)


def test_missed_escalation_is_reported() -> None:
    assert score(TICKETS, PREDICTIONS)["missed_escalations"] == ["c"]


def test_unanswered_tickets_are_left_out() -> None:
    # Ticket "c" got no prediction (e.g. a timeout): it is not counted as right or wrong.
    result = score(TICKETS, {"a": prediction()})
    assert result["n"] == 1
    assert result["category_ci"] == wilson_interval(1, 1)


def test_nothing_classified_scores_nothing() -> None:
    assert score(TICKETS, {}) == {"n": 0}
