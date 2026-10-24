"""Settings that change between environments (my laptop, CI, a server), checked once at startup.

Rules that change results (MIN_SCORE, vector size, prompts) stay in code on purpose:
changing them must be a reviewed commit followed by a new evaluation, not a quiet .env edit.
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from helpdesk.core.paths import ROOT


class Settings(BaseSettings):
    """Read from environment variables first, then from .env (names are not case-sensitive)."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    gemini_api_key: SecretStr  # SecretStr prints as '**********', so the key never lands in logs
    gemini_model: str
    gemini_timeout_seconds: float = Field(default=60, gt=0)  # one request once hung for 30+ min
    gemini_retry_attempts: int = Field(default=5, ge=1)  # tries in total, counting the first
    # Paid-tier prices in USD per 1M tokens, for the cost estimate in the logs (the free tier costs
    # nothing). Source: ai.google.dev/gemini-api/docs/pricing, checked 2026-10-11, gemini-3.5-flash-lite.
    price_input_per_million: float = Field(default=0.30, ge=0)
    price_output_per_million: float = Field(
        default=2.50, ge=0
    )  # thinking tokens are billed as output


@lru_cache
def get_settings() -> Settings:
    """Load and check the settings on first use, then reuse the same object."""
    return Settings()
