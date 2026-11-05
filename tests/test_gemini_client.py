"""Tests for the shared Gemini client (no Gemini calls: the client class is faked)."""

import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace

import httpx
import pytest
from google import genai
from google.genai import errors

from helpdesk.ai import gemini
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


# The backup model: when Google's main model is overloaded, the live site still answers.
LABELS_JSON = '{"reason": "r", "category": "billing", "priority": "low", "escalate": false}'


class FakeGemini:
    """The main model fails with `failure`; the backup model answers. Records which models were asked."""

    def __init__(self) -> None:
        self.failure: Exception = errors.ServerError(503, {"error": {"code": 503}})
        self.models: list[str] = []

    def generate(self, stage: str, contents: str, config: object, model: str) -> object:
        self.models.append(model)
        if model == "main-model":
            raise self.failure
        return SimpleNamespace(text=LABELS_JSON)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeGemini:
    fake = FakeGemini()
    settings = SimpleNamespace(gemini_model="main-model", gemini_fallback_model="backup-model")
    monkeypatch.setattr(gemini, "get_gemini_settings", lambda: settings)
    monkeypatch.setattr(gemini, "generate", fake.generate)
    return fake


def ask(use_fallback: bool) -> Classification:
    provider = gemini.GeminiProvider(use_fallback=use_fallback)
    return provider.generate_json("classify", "system", "ticket", Classification, "high")


@pytest.mark.parametrize(
    "failure",
    [
        errors.ServerError(503, {"error": {"code": 503}}),  # "high demand"
        errors.ServerError(504, {"error": {"code": 504}}),  # deadline exceeded
        errors.ClientError(429, {"error": {"code": 429}}),  # the main model's free quota is used up
        httpx.ReadTimeout("no answer in time"),
    ],
)
def test_an_overloaded_main_model_falls_back_to_the_backup(
    fake: FakeGemini, failure: Exception
) -> None:
    fake.failure = failure
    assert ask(use_fallback=True).category == "billing"
    assert fake.models == ["main-model", "backup-model"]


def test_evals_never_fall_back(fake: FakeGemini) -> None:
    # A score must measure ONE model: a backup answer must not slip into it.
    with pytest.raises(errors.ServerError):
        ask(use_fallback=False)
    assert fake.models == ["main-model"]


def test_a_bad_request_does_not_fall_back(fake: FakeGemini) -> None:
    # 400 means our request is wrong: another model would not fix it, and the error must be seen.
    fake.failure = errors.ClientError(400, {"error": {"code": 400}})
    with pytest.raises(errors.ClientError):
        ask(use_fallback=True)
    assert fake.models == ["main-model"]
