"""Gemini: one client (created on first use, with timeout and retries) and the LLMProvider for it."""

import time
from functools import lru_cache

from google import genai
from google.genai import types

from helpdesk.ai.provider import Output, Thinking
from helpdesk.core.logs import get_logger
from helpdesk.core.settings import get_gemini_settings

logger = get_logger(__name__)


@lru_cache
def get_client() -> genai.Client:
    """The Gemini client, created on first use (so importing this file needs no API key)."""
    settings = get_gemini_settings()
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
    settings = get_gemini_settings()
    output = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return (
        (usage.prompt_token_count or 0) * settings.price_input_per_million
        + output * settings.price_output_per_million
    ) / 1_000_000


def generate(
    stage: str, contents: str, config: types.GenerateContentConfig
) -> types.GenerateContentResponse:
    """One Gemini call, timed and logged (tokens, estimated cost). Never logs the contents."""
    model = get_gemini_settings().gemini_model
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


THINKING_LEVELS = {"low": types.ThinkingLevel.LOW, "high": types.ThinkingLevel.HIGH}


class GeminiProvider:
    """The LLMProvider for Gemini: structured output in the given schema, the thinking level, and
    no function calling. Temperature is NOT set: Gemini 3 should stay at its default 1.0 (Google's
    advice); consistency comes from the schema and clear rules, and is measured by running twice."""

    @property
    def model(self) -> str:
        return get_gemini_settings().gemini_model

    def generate_json(
        self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
    ) -> Output:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),  # Gemini must answer in this shape
            thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVELS[thinking]),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        return schema.model_validate_json(response_text(generate(stage, contents, config)))
