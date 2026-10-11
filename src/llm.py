"""Shared Gemini setup: one client, created on first use, with timeout and retries."""

import time
from functools import lru_cache

from google import genai
from google.genai import types

from config import get_settings
from logs import get_logger

logger = get_logger(__name__)


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


def estimated_cost(usage: types.GenerateContentResponseUsageMetadata | None) -> float:
    """What the call would cost on the paid tier, in USD (thinking tokens are billed as output)."""
    if usage is None:
        return 0.0
    settings = get_settings()
    output = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return (
        (usage.prompt_token_count or 0) * settings.price_input_per_million
        + output * settings.price_output_per_million
    ) / 1_000_000


def generate(
    stage: str, contents: str, config: types.GenerateContentConfig
) -> types.GenerateContentResponse:
    """One Gemini call, timed and logged (tokens, estimated cost). Never logs the contents."""
    model = get_settings().gemini_model
    started = time.perf_counter()
    response = get_client().models.generate_content(model=model, contents=contents, config=config)
    usage = response.usage_metadata
    logger.info(
        "gemini_call",
        stage=stage,
        model=model,
        ms=round((time.perf_counter() - started) * 1000),
        input_tokens=usage.prompt_token_count if usage else None,
        output_tokens=usage.candidates_token_count if usage else None,
        thinking_tokens=usage.thoughts_token_count if usage else None,
        cost_usd=round(estimated_cost(usage), 6),
    )
    return response


def response_text(response: types.GenerateContentResponse) -> str:
    """The reply text, or a clear error when Gemini returned none (e.g. blocked by a safety filter)."""
    if not response.text:
        reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
        raise RuntimeError(f"Gemini returned no text (finish reason: {reason}).")
    return response.text


def ask(prompt: str) -> str:
    """Send one prompt to Gemini and return its text reply."""
    return response_text(generate("ask", prompt, NO_AFC))
