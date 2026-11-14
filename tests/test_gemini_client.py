"""Tests for the shared Gemini client (no Gemini calls: the client class is faked)."""

import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace

import httpx
import pytest
from google import genai
from google.genai import errors, types

from helpdesk.ai import gemini
from helpdesk.ai.resilience import ModelHealth, NoModelAnswered
from helpdesk.domain.outputs import Classification


class SlowClient:
    """Takes a while to build, so threads that start together all ask before it is cached."""

    def __init__(self, **_kwargs: object) -> None:
        time.sleep(0.05)


@pytest.fixture
def fresh_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    settings = SimpleNamespace(
        gemini_api_key=SimpleNamespace(get_secret_value=lambda: "test-key"),
        gemini_retry_attempts=2,
        gemini_timeout_seconds=25,
    )
    monkeypatch.setattr(gemini, "get_gemini_settings", lambda: settings)
    monkeypatch.setattr(genai, "Client", SlowClient)
    gemini.new_client.cache_clear()
    yield
    gemini.new_client.cache_clear()  # later tests must not get the fake client


def test_threads_starting_together_share_one_client(fresh_client: None) -> None:
    # The classifier runs in its own thread (pipeline.py). A second client built at the same moment
    # is thrown away and closed while its request is still running ("client has been closed").
    start = threading.Barrier(8)
    clients: list[object] = []

    def ask() -> None:
        start.wait()
        clients.append(gemini.get_client())

    threads = [threading.Thread(target=ask) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len({id(client) for client in clients}) == 1


# The live model chain (docs/decisions/0018): a busy model hands over to the next one; evals measure
# exactly one model. The chain's timing (hedging, deadline, resting models) is in test_resilience.py.
LABELS_JSON = '{"reason": "r", "category": "billing", "priority": "low", "escalate": false}'


class FakeGemini:
    """Each model answers LABELS_JSON unless `failures` holds an error (or broken text) for it.
    Records which models were asked and with which config."""

    def __init__(self) -> None:
        self.failures: dict[str, Exception | str] = {
            "first": errors.ServerError(503, {"error": {"code": 503}})
        }
        self.models: list[str] = []
        self.configs: list[types.GenerateContentConfig] = []
        self.lock = threading.Lock()

    def generate(
        self, stage: str, contents: str, config: types.GenerateContentConfig, model: str
    ) -> object:
        with self.lock:
            self.models.append(model)
            self.configs.append(config)
        failure = self.failures.get(model)
        if isinstance(failure, Exception):
            raise failure
        return SimpleNamespace(text=failure if isinstance(failure, str) else LABELS_JSON)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeGemini:
    fake = FakeGemini()
    settings = SimpleNamespace(gemini_model="eval-model", gemini_live_models=["first", "second"])
    monkeypatch.setattr(gemini, "get_gemini_settings", lambda: settings)
    monkeypatch.setattr(gemini, "generate", fake.generate)
    monkeypatch.setattr(gemini, "HEALTH", ModelHealth(skip_seconds=60))  # fresh per test
    return fake


def ask(live: bool) -> Classification:
    provider = gemini.GeminiProvider(live=live)
    return provider.generate_json("classify", "system", "ticket", Classification, "high")


@pytest.mark.parametrize(
    "failure",
    [
        errors.ServerError(503, {"error": {"code": 503}}),  # "high demand"
        errors.ServerError(504, {"error": {"code": 504}}),  # deadline exceeded
        errors.ServerError(500, {"error": {"code": 500}}),
        errors.ClientError(429, {"error": {"code": 429}}),  # this model's free quota is used up
        httpx.ReadTimeout("no answer in time"),
        "not json",  # a broken answer: another model may answer properly
    ],
)
def test_a_failing_live_model_hands_over_to_the_next(
    fake: FakeGemini, failure: Exception | str
) -> None:
    fake.failures = {"first": failure}
    assert ask(live=True).category == "billing"
    assert fake.models == ["first", "second"]


def test_evals_measure_one_model_and_never_use_the_chain(fake: FakeGemini) -> None:
    fake.failures = {"eval-model": errors.ServerError(503, {"error": {"code": 503}})}
    with pytest.raises(errors.ServerError):
        ask(live=False)
    assert fake.models == ["eval-model"]


def test_live_calls_have_short_limits_in_code(fake: FakeGemini) -> None:
    # No hosting setting is needed: one try per model (the next model is faster than a retry), and a
    # call never outlives the deadline, so abandoned hedged calls end on their own.
    ask(live=True)
    for config in fake.configs:
        assert config.http_options is not None
        assert config.http_options.timeout == int(gemini.LIVE_DEADLINE_SECONDS * 1000)
        assert config.http_options.retry_options is not None
        assert config.http_options.retry_options.attempts == 1


def test_evals_keep_the_patient_client_limits(fake: FakeGemini) -> None:
    # Evals must not lose tickets to a slow minute: they keep GEMINI_TIMEOUT_SECONDS and retries.
    fake.failures = {}
    ask(live=False)
    assert fake.configs[0].http_options is None


def test_a_bad_request_is_not_passed_on(fake: FakeGemini) -> None:
    # 400 means our request is wrong: another model would not fix it, and the error must be seen.
    fake.failures = {"first": errors.ClientError(400, {"error": {"code": 400}})}
    with pytest.raises(errors.ClientError):
        ask(live=True)
    assert fake.models == ["first"]


def test_when_every_live_model_fails_the_student_gets_a_clear_error(fake: FakeGemini) -> None:
    busy = errors.ServerError(503, {"error": {"code": 503}})
    fake.failures = {"first": busy, "second": busy}
    with pytest.raises(NoModelAnswered):
        ask(live=True)


def test_a_model_that_just_failed_is_asked_last_on_the_next_ticket(fake: FakeGemini) -> None:
    ask(live=True)  # "first" was busy
    fake.failures = {}
    ask(live=True)
    assert fake.models == ["first", "second", "second"]
