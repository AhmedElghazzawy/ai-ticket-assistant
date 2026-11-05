"""Gemini: one client (created on first use, with timeout and retries) and the LLMProvider for it."""

import threading
import time
from functools import lru_cache

import httpx
from google import genai
from google.genai import errors, types

from helpdesk.ai.provider import Output, Thinking
from helpdesk.core.logs import get_logger
from helpdesk.core.settings import get_gemini_settings

logger = get_logger(__name__)


# lru_cache alone may build the client twice when two threads ask at once (the classifier runs in
# its own thread); the extra client is then thrown away and closed during its request.
CLIENT_LOCK = threading.Lock()


def get_client() -> genai.Client:
    """The Gemini client, created on first use (so importing this file needs no API key)."""
    with CLIENT_LOCK:
        return new_client()


@lru_cache
def new_client() -> genai.Client:
    """Build the client once; only called through get_client, under the lock."""
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
    stage: str, contents: str, config: types.GenerateContentConfig, model: str
) -> types.GenerateContentResponse:
    """One Gemini call, timed and logged (tokens, estimated cost). Never logs the contents."""
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
    return response_text(generate("ask", prompt, NO_AFC, get_gemini_settings().gemini_model))


THINKING_LEVELS = {"low": types.ThinkingLevel.LOW, "high": types.ThinkingLevel.HIGH}


# Google's side is busy or slow, or the main model's quota is used up: another model can still answer.
# A 400 is not here: it means our request is wrong, and another model would not fix that.
OVERLOADED = {429, 500, 503, 504}


# After an overload the main model is skipped for a while: Google takes ~20 s to answer "busy", so
# asking a model we know is down first made every answer take ~60 s (live, 2026-11-05).
SKIP_MAIN_SECONDS = 300
clock = time.monotonic  # a function, so tests can move time forward
main_down_until = 0.0  # clock time until which the live API goes straight to the backup


def is_overloaded(error: Exception) -> bool:
    if isinstance(error, httpx.TimeoutException):
        return True
    return isinstance(error, errors.APIError) and error.code in OVERLOADED


class GeminiProvider:
    """The LLMProvider for Gemini: structured output in the given schema, the thinking level, and
    no function calling. Temperature is NOT set: Gemini 3 should stay at its default 1.0 (Google's
    advice); consistency comes from the schema and clear rules, and is measured by running twice.

    With `use_fallback` (the live API only), a call that fails because the main model is overloaded
    is asked once more on GEMINI_FALLBACK_MODEL, so a busy model does not take the site down."""

    def __init__(self, use_fallback: bool = False) -> None:
        self.use_fallback = use_fallback

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
        fallback = get_gemini_settings().gemini_fallback_model if self.use_fallback else None
        if fallback and clock() < main_down_until:
            response = generate(stage, contents, config, fallback)  # the main model is resting
        else:
            try:
                response = generate(stage, contents, config, self.model)
            except Exception as error:
                if not (fallback and is_overloaded(error)):
                    raise
                mark_main_down()
                logger.warning(
                    "gemini_fallback", stage=stage, error_type=type(error).__name__, model=fallback
                )
                response = generate(stage, contents, config, fallback)
        return schema.model_validate_json(response_text(response))


def mark_main_down() -> None:
    """Skip the main model for SKIP_MAIN_SECONDS. A plain float write: the worst a race between the
    two pipeline threads can do is set almost the same time twice."""
    global main_down_until
    main_down_until = clock() + SKIP_MAIN_SECONDS
