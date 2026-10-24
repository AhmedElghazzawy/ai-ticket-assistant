"""Settings that change between environments (my laptop, CI, a server), checked once at startup.

The ONLY module that reads environment variables. Two groups, because they are needed at different
times: the app settings (database, logs, cookies, limits) must work on a machine without a Gemini
key (tests, CI, tools); the Gemini settings are loaded on the first model call.

Rules that change results (MIN_SCORE, vector size, prompts) stay in code on purpose:
changing them must be a reviewed commit followed by a new evaluation, not a quiet .env edit.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from helpdesk.core.paths import ROOT

# Read from environment variables first, then from .env (names are not case-sensitive).
ENV = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


class AppSettings(BaseSettings):
    """The server and its database. A bad value stops the app at startup with a clear error."""

    model_config = ENV

    # The default is the local Docker database (compose.yaml); production sets Neon's address.
    # SecretStr: the password inside the URL never appears when settings are printed or logged.
    database_url: SecretStr = SecretStr("postgresql://helpdesk:local-only@127.0.0.1:5433/helpdesk")
    log_format: Literal["console", "json"] = "console"  # json: one object per line (servers)
    # Secure cookies are only sent over https; false only for plain-http local development.
    cookie_secure: bool = True
    demo_mode: bool = False  # the public demo: a one-click staff login with sample tickets only
    # The header in which the hosting proxy puts the real visitor address (Render:
    # CF-Connecting-IP). Empty: no header is trusted, because a visitor could fake it.
    client_ip_header: str = ""
    # The whole system's tickets per day (UTC): at ~$0.0074 per ticket, 300 cost at most ~$2.20.
    daily_ticket_cap: int = Field(default=300, ge=0)

    @field_validator("log_format", "client_ip_header", mode="before")
    @classmethod
    def lower_case(cls, value: object) -> object:
        """LOG_FORMAT=JSON works too, and HTTP header names ignore case."""
        return value.lower() if isinstance(value, str) else value


class GeminiSettings(BaseSettings):
    """The model connection. Loaded on first use, so importing the app needs no API key."""

    model_config = ENV

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
def get_app_settings() -> AppSettings:
    """Load and check the app settings on first use, then reuse the same object."""
    return AppSettings()


@lru_cache
def get_gemini_settings() -> GeminiSettings:
    """Load and check the Gemini settings on first use, then reuse the same object."""
    return GeminiSettings()
