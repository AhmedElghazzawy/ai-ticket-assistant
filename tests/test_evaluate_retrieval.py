"""Tests for the retrieval eval's summary: hand-made rows, no AI calls."""

from typing import Any

from evaluate_retrieval import summarize
from stats import wilson_interval


def row(expected: str, hit1: bool, hit3: bool, score: float = 0.8) -> dict[str, Any]:
    return {"id": expected, "expected": expected, "top_score": score, "hit1": hit1, "hit3": hit3}


ROWS = [
    row("sinavlar", hit1=True, hit3=True),
    row("staj", hit1=False, hit3=True),
    row("harc", hit1=False, hit3=False),
    row("none", hit1=False, hit3=False, score=0.5),  # no document answers it: not counted
]


def test_hit_rates_come_with_their_interval() -> None:
    summary = summarize(ROWS)
    assert summary["answerable"] == 3
    assert summary["hit@3"] == 2 / 3
    assert summary["hit@3_ci"] == wilson_interval(2, 3)
    assert summary["hit@1_ci"] == wilson_interval(1, 3)


def test_misses_and_unanswerable_scores_are_reported() -> None:
    summary = summarize(ROWS)
    assert summary["misses"] == ["harc"]
    assert summary["top_score_none"] == [0.5, 0.5]
