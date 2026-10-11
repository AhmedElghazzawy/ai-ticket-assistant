"""Shared Gemini setup: one client, created on first use, with timeout and retries."""

from functools import lru_cache

from google import genai
from google.genai import types

from config import get_settings


@lru_cache
def get_client() -> genai.Client:
    """The Gemini client, created on first use (so importing this file needs no API key)."""
    settings = get_settings()
    # If Google answers "too busy" (429) or has a server error (500, 503),
    # wait and try again: 2s, then 4s, 8s, 16s (each wait doubles).
    retry = types.HttpRetryOptions(
        attempts=settings.gemini_retry_attempts,
        initial_delay=2.0,
        http_status_codes=[429, 500, 503],
    )
    return genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        # give up on a request after the timeout; the retry logic then tries again
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_timeout_seconds * 1000),  # Google wants milliseconds
            retry_options=retry,
        ),
    )


# We never let the model call Python functions, so switch that feature off.
NO_AFC = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


def response_text(response: types.GenerateContentResponse) -> str:
    """The reply text, or a clear error when Gemini returned none (e.g. blocked by a safety filter)."""
    if not response.text:
        reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
        raise RuntimeError(f"Gemini returned no text (finish reason: {reason}).")
    return response.text


def ask(prompt: str) -> str:
    """Send one prompt to Gemini and return its text reply."""
    response = get_client().models.generate_content(
        model=get_settings().gemini_model, contents=prompt, config=NO_AFC
    )
    return response_text(response)
