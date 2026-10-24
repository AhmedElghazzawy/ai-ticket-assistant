"""Tests for the Wilson confidence interval: hand-checked values, no AI calls."""

import pytest

from helpdesk.evals.stats import wilson_interval


def test_all_correct_is_not_certain() -> None:
    # 17/17 (hit@3 on the locked test set): the README reports about 82%-100%.
    low, high = wilson_interval(17, 17)
    assert low == pytest.approx(0.8157, abs=1e-4)
    assert high == 1.0


def test_half_correct_is_symmetric() -> None:
    # 5/10: textbook Wilson values, centered on 50%.
    low, high = wilson_interval(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-4)
    assert high == pytest.approx(0.7634, abs=1e-4)


def test_none_correct_starts_at_zero() -> None:
    low, high = wilson_interval(0, 14)
    assert low == 0.0
    assert 0.0 < high < 0.25


def test_bigger_sample_gives_narrower_interval() -> None:
    small = wilson_interval(8, 10)
    big = wilson_interval(80, 100)
    assert big[1] - big[0] < small[1] - small[0]


@pytest.mark.parametrize(("successes", "n"), [(1, 0), (-1, 5), (6, 5)])
def test_impossible_counts_are_refused(successes: int, n: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(successes, n)
