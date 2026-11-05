"""Tests for the shared Gemini client (no Gemini calls: the client class is faked)."""

import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from google import genai

from helpdesk.ai import gemini


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
