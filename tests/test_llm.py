"""response_text(): a missing reply must give a clear error, not a confusing JSON error later."""

import pytest
from google.genai import types

from helpdesk.ai.gemini import response_text


def make_response(text: str | None, reason: types.FinishReason) -> types.GenerateContentResponse:
    """A hand-made Gemini response, so the test needs no API call."""
    parts = [types.Part(text=text)] if text is not None else []
    content = types.Content(role="model", parts=parts)
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=content, finish_reason=reason)]
    )


def test_returns_the_text() -> None:
    response = make_response('{"category": "other"}', types.FinishReason.STOP)
    assert response_text(response) == '{"category": "other"}'


def test_blocked_reply_raises_with_the_reason() -> None:
    response = make_response(None, types.FinishReason.SAFETY)
    with pytest.raises(RuntimeError, match="SAFETY"):
        response_text(response)
