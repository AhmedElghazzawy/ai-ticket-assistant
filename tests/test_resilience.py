"""Tests for the live model chain (docs/decisions/0018): busy models are skipped, slow ones are
hedged, and a student never waits past the deadline. Real threads, fake models, tiny times."""

import threading
import time
from collections.abc import Callable

import pytest

from helpdesk.ai.resilience import ModelHealth, NoModelAnswered, first_answer


class Busy(Exception):
    """Stands in for a 503 / 429 / timeout: another model may answer."""


class BadRequest(Exception):
    """Stands in for a 400: our request is wrong, another model would not fix it."""


def retryable(error: Exception) -> bool:
    return isinstance(error, Busy)


class Models:
    """Fake models: each name maps to (seconds before it answers, error to raise or None)."""

    def __init__(self, behaviour: dict[str, tuple[float, Exception | None]]) -> None:
        self.behaviour = behaviour
        self.asked: list[str] = []
        self.lock = threading.Lock()

    def __call__(self, model: str) -> str:
        with self.lock:
            self.asked.append(model)
        delay, error = self.behaviour[model]
        time.sleep(delay)
        if error is not None:
            raise error
        return f"answer from {model}"


def run(
    models: Models, health: ModelHealth | None = None, hedge: float = 0.2, deadline: float = 1.0
) -> str:
    return first_answer(
        list(models.behaviour),
        models,
        retryable=retryable,
        hedge_after=hedge,
        deadline=deadline,
        health=health or ModelHealth(skip_seconds=60),
    )


def test_a_healthy_first_model_answers_alone() -> None:
    models = Models({"a": (0.0, None), "b": (0.0, None)})
    assert run(models) == "answer from a"
    assert models.asked == ["a"]


def test_a_busy_model_passes_to_the_next_at_once() -> None:
    models = Models({"a": (0.0, Busy()), "b": (0.0, Busy()), "c": (0.0, None)})
    started = time.perf_counter()
    assert run(models, hedge=5.0) == "answer from c"
    assert time.perf_counter() - started < 1.0  # no waiting for the hedge timer after a fast "busy"
    assert models.asked == ["a", "b", "c"]


def test_a_slow_model_is_hedged_and_the_first_answer_wins() -> None:
    models = Models({"a": (2.0, None), "b": (0.05, None)})
    started = time.perf_counter()
    assert run(models, hedge=0.1, deadline=3.0) == "answer from b"
    assert time.perf_counter() - started < 1.0  # did not wait for the slow model
    assert models.asked == ["a", "b"]


def test_a_bad_request_is_raised_without_asking_other_models() -> None:
    models = Models({"a": (0.0, BadRequest()), "b": (0.0, None)})
    with pytest.raises(BadRequest):
        run(models)
    assert models.asked == ["a"]


def test_when_every_model_is_busy_the_last_error_is_reported() -> None:
    models = Models({"a": (0.0, Busy()), "b": (0.0, Busy())})
    with pytest.raises(NoModelAnswered) as caught:
        run(models)
    assert isinstance(caught.value.__cause__, Busy)


def test_nobody_waits_past_the_deadline() -> None:
    models = Models({"a": (3.0, None), "b": (3.0, None)})
    started = time.perf_counter()
    with pytest.raises(NoModelAnswered):
        run(models, hedge=0.1, deadline=0.3)
    assert time.perf_counter() - started < 1.0


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def health_with(clock: Callable[[], float]) -> ModelHealth:
    return ModelHealth(skip_seconds=60, clock=clock)


def test_a_model_that_just_failed_is_asked_last_for_a_while() -> None:
    clock = Clock()
    health = health_with(clock)
    run(Models({"a": (0.0, Busy()), "b": (0.0, None)}), health)
    later = Models({"a": (0.0, None), "b": (0.0, None)})
    clock.now += 59
    assert run(later, health) == "answer from b"  # a is resting: b goes first
    assert later.asked == ["b"]


def test_a_resting_model_is_still_a_last_resort_and_returns_after_the_pause() -> None:
    clock = Clock()
    health = health_with(clock)
    run(Models({"a": (0.0, Busy()), "b": (0.0, None)}), health)
    only_a_works = Models({"a": (0.0, None), "b": (0.0, Busy())})
    assert run(only_a_works, health) == "answer from a"  # resting, but better than no answer
    clock.now += 61
    back = Models({"a": (0.0, None), "b": (0.0, None)})
    run(back, health)
    assert back.asked == ["a"]  # both pauses are over: the normal order again


def test_a_model_that_lost_the_race_rests_too() -> None:
    # A slow model never fails, it just never answers: without this, every next ticket would wait
    # for the hedge timer again (seen live on 2026-11-14: 14 s twice in a row).
    health = ModelHealth(skip_seconds=60)
    run(Models({"a": (1.0, None), "b": (0.0, None)}), health, hedge=0.1, deadline=3.0)
    next_ticket = Models({"a": (0.0, None), "b": (0.0, None)})
    assert run(next_ticket, health) == "answer from b"
    assert next_ticket.asked == ["b"]
