"""The question's embedding: short limits, because a student waits for it (docs/decisions/0018)."""

from types import SimpleNamespace

import pytest
from google.genai import types

from helpdesk.retrieval import embeddings


class FakeClient:
    def __init__(self) -> None:
        self.configs: list[types.EmbedContentConfig] = []
        self.models = self

    def embed_content(
        self, model: str, contents: list[object], config: types.EmbedContentConfig
    ) -> object:
        self.configs.append(config)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1]) for _ in contents])


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    fake = FakeClient()
    monkeypatch.setattr(embeddings, "get_client", lambda: fake)
    return fake


def test_a_question_is_embedded_with_short_limits_and_quick_retries(client: FakeClient) -> None:
    assert embeddings.embed_query("Harç ne zaman?") == [0.1]
    options = client.configs[0].http_options
    assert options is not None and options.timeout == 8_000  # milliseconds, not the 60 s eval limit
    assert options.retry_options is not None and options.retry_options.attempts == 3
    assert options.retry_options.initial_delay == 0.5


def test_indexing_documents_keeps_the_patient_client_limits(client: FakeClient) -> None:
    embeddings.embed(["a document"])
    assert client.configs[0].http_options is None
