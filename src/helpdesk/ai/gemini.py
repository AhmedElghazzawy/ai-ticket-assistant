"""Gemini: one client (created on first use, with timeout and retries) and the LLMProvider for it."""

import threading
import time
from functools import lru_cache

import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from helpdesk.ai.provider import Output, Thinking
from helpdesk.ai.resilience import ModelHealth, first_answer
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
    # Patient limits for indexing and evals: exponential backoff on 429/500/503, starting at 2 s.
    retry = types.HttpRetryOptions(
        attempts=settings.gemini_retry_attempts,
        initial_delay=2.0,
        http_status_codes=[429, 500, 503],
    )
    return genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_timeout_seconds * 1000),  # Google wants milliseconds
            retry_options=retry,
        ),
    )


# The model only returns JSON; it never calls our code.
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


# Google's side is busy or slow, or this model's quota is used up: another model can still answer.
# A 400 is not here: it means our request is wrong, and another model would not fix that.
OVERLOADED = {429, 500, 503, 504}

# The live API's timing (docs/decisions/0018), in code so it never depends on a hosting dashboard.
# A healthy answer takes 2-8 s (measured 2026-11-14); after 9 s the next model races the slow one,
# and nobody waits more than 25 s for one step. One try per model: the next model beats a retry.
LIVE_HEDGE_SECONDS = 9.0
LIVE_DEADLINE_SECONDS = 25.0
LIVE_LIMITS = types.HttpOptions(
    timeout=int(LIVE_DEADLINE_SECONDS * 1000),  # milliseconds: an abandoned call ends by itself
    retry_options=types.HttpRetryOptions(attempts=1),
)
# A model that failed is asked last for 2 minutes: Google's overloads usually pass within minutes.
HEALTH = ModelHealth(skip_seconds=120)


def is_retryable(error: Exception) -> bool:
    """Another model may succeed: busy, slow, out of quota, a dropped connection, or a broken answer."""
    # TransportError covers timeouts, dropped connections (RemoteProtocolError) and refused ones.
    if isinstance(error, httpx.TransportError | ValidationError):
        return True
    if isinstance(error, RuntimeError) and "returned no text" in str(error):
        return True
    return isinstance(error, errors.APIError) and error.code in OVERLOADED


class GeminiProvider:
    """The LLMProvider for Gemini: structured output in the given schema, the thinking level, and
    no function calling. Temperature is NOT set: Gemini 3 should stay at its default 1.0 (Google's
    advice); consistency comes from the schema and clear rules, and is measured by running twice.

    `live=True` (the live API only) asks the GEMINI_LIVE_MODELS chain with short limits and hedging,
    so a busy or slow model does not fail the student. Otherwise (evals, tools) exactly one model is
    measured, with the client's patient limits."""

    def __init__(self, live: bool = False, model: str | None = None) -> None:
        self.live = live
        self.chosen_model = model  # e.g. for a model comparison; None: GEMINI_MODEL

    @property
    def model(self) -> str:
        return self.chosen_model or get_gemini_settings().gemini_model

    def generate_json(
        self, stage: str, system: str, contents: str, schema: type[Output], thinking: Thinking
    ) -> Output:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),  # Gemini must answer in this shape
            thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVELS[thinking]),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=LIVE_LIMITS if self.live else None,  # None: the client's limits
        )

        def answer_from(model: str) -> Output:
            # Parsing inside: a broken answer from one model hands over to the next one.
            return schema.model_validate_json(
                response_text(generate(stage, contents, config, model))
            )

        if not self.live:
            return answer_from(self.model)
        return first_answer(
            get_gemini_settings().gemini_live_models,
            answer_from,
            retryable=is_retryable,
            hedge_after=LIVE_HEDGE_SECONDS,
            deadline=LIVE_DEADLINE_SECONDS,
            health=HEALTH,
        )
