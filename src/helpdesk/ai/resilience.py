"""Get one answer from a chain of models, fast, even when some of them are busy or slow
(docs/decisions/0018). Pure orchestration: it knows nothing about Gemini, so it is tested with fakes.

- A model that answers "busy" (503, 429, timeout) passes the work to the next model at once.
- A model that is slow gets company: after `hedge_after` seconds the next model starts too, and the
  first answer wins ("hedged requests", from Google's "The Tail at Scale").
- A model that just failed, or lost a race, is asked last for `skip_seconds`, but is still a last resort.
- Nobody waits past `deadline`.
"""

import contextvars
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait


class NoModelAnswered(Exception):
    """Every model was busy, or none answered before the deadline."""


class ModelHealth:
    """Which models failed recently. Shared by every request of one process (thread-safe)."""

    def __init__(self, skip_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.skip_seconds = skip_seconds
        self.clock = clock
        self.down_until: dict[str, float] = {}
        self.lock = threading.Lock()

    def mark_down(self, model: str) -> None:
        with self.lock:
            self.down_until[model] = self.clock() + self.skip_seconds

    def in_order(self, models: list[str]) -> list[str]:
        """The models that are fine first (in their order), then the resting ones."""
        now = self.clock()
        with self.lock:
            resting = {m for m in models if self.down_until.get(m, 0.0) > now}
        return [m for m in models if m not in resting] + [m for m in models if m in resting]


def first_answer[T](
    models: list[str],
    call: Callable[[str], T],
    *,
    retryable: Callable[[Exception], bool],
    hedge_after: float,
    deadline: float,
    health: ModelHealth,
) -> T:
    """The first successful `call(model)`. A non-retryable error (our request is wrong) is raised
    at once; when every model failed or the deadline passed, NoModelAnswered (from the last error)."""
    waiting = health.in_order(models)
    end = time.monotonic() + deadline
    # Not a `with` block: leaving it would wait for the slow calls we no longer need. They end on
    # their own HTTP timeout; their answers are simply ignored.
    pool = ThreadPoolExecutor(max_workers=len(models), thread_name_prefix="model")
    running: dict[Future[T], str] = {}
    last_error: Exception | None = None

    def start_next() -> None:
        model = waiting.pop(0)
        # Each thread gets a copy of this request's context, so its logs keep the request_id.
        running[pool.submit(contextvars.copy_context().run, call, model)] = model

    try:
        start_next()
        while running:
            left = end - time.monotonic()
            if left <= 0:
                break
            done, _ = wait(running, timeout=min(hedge_after, left), return_when=FIRST_COMPLETED)
            if not done:  # the current models are slow: let the next one race them
                if waiting:
                    start_next()
                continue
            for future in done:
                model = running.pop(future)
                error = future.exception()
                if error is None:
                    for slower in running.values():  # lost the race: too slow right now
                        health.mark_down(slower)
                    return future.result()
                if not isinstance(error, Exception) or not retryable(error):
                    raise error
                health.mark_down(model)
                last_error = error
            if not running and waiting:
                start_next()  # busy and nothing else running: pass the work on at once
        raise NoModelAnswered("No model answered in time.") from last_error
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
