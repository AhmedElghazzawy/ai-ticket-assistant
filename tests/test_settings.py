"""Settings: checked at startup, clear errors, and secrets never printed."""

import pytest
from pydantic import ValidationError

from helpdesk.core.settings import AppSettings, GeminiSettings

VARIABLES = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_TIMEOUT_SECONDS",
    "DATABASE_URL",
    "LOG_FORMAT",
    "COOKIE_SECURE",
    "DEMO_MODE",
    "CLIENT_IP_HEADER",
    "DAILY_TICKET_CAP",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test with none of our variables, whatever is set on this computer."""
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)


def load_gemini(monkeypatch: pytest.MonkeyPatch, **values: str) -> GeminiSettings:
    """Settings from the given variables only; _env_file=None so the real .env is never read."""
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return GeminiSettings(_env_file=None)


def load_app(monkeypatch: pytest.MonkeyPatch, **values: str) -> AppSettings:
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return AppSettings(_env_file=None)


def test_reads_settings_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_gemini(monkeypatch, GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
    assert settings.gemini_model == "test-model"
    assert settings.gemini_api_key.get_secret_value() == "test-key"
    assert settings.gemini_timeout_seconds == 60


def test_missing_key_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="gemini_api_key"):
        load_gemini(monkeypatch, GEMINI_MODEL="test-model")


def test_wrong_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="gemini_timeout_seconds"):
        load_gemini(monkeypatch, GEMINI_API_KEY="k", GEMINI_MODEL="m", GEMINI_TIMEOUT_SECONDS="-5")


def test_key_is_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_gemini(monkeypatch, GEMINI_API_KEY="super-secret", GEMINI_MODEL="m")
    assert "super-secret" not in str(settings)
    assert "super-secret" not in repr(settings)


def test_app_settings_need_no_api_key_and_have_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The database, logs and tools must work on a machine without a Gemini key (tests, CI).
    settings = load_app(monkeypatch)
    assert settings.log_format == "console"
    assert settings.cookie_secure is True  # production default: cookies only over https
    assert settings.demo_mode is False
    assert settings.client_ip_header == ""  # no proxy header trusted unless named
    assert settings.daily_ticket_cap == 300
    assert "127.0.0.1:5433" in settings.database_url.get_secret_value()  # compose.yaml's Postgres


def test_app_settings_read_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_app(
        monkeypatch,
        DATABASE_URL="postgresql://u:p@neon.example/db",
        LOG_FORMAT="JSON",
        COOKIE_SECURE="false",
        DEMO_MODE="true",
        CLIENT_IP_HEADER="CF-Connecting-IP",
        DAILY_TICKET_CAP="2",
    )
    assert settings.database_url.get_secret_value() == "postgresql://u:p@neon.example/db"
    assert settings.log_format == "json"
    assert settings.cookie_secure is False
    assert settings.demo_mode is True
    assert settings.client_ip_header == "cf-connecting-ip"  # HTTP header names ignore case
    assert settings.daily_ticket_cap == 2


@pytest.mark.parametrize(
    ("name", "value"),
    [("LOG_FORMAT", "xml"), ("DEMO_MODE", "maybe"), ("DAILY_TICKET_CAP", "-1")],
)
def test_a_bad_app_setting_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    # Before, a typo was silently read as the default (e.g. DEMO_MODE=ture meant "off").
    with pytest.raises(ValidationError, match=name.lower()):
        load_app(monkeypatch, **{name: value})


def test_database_password_is_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load_app(monkeypatch, DATABASE_URL="postgresql://u:hunter2@neon.example/db")
    assert "hunter2" not in str(settings)
    assert "hunter2" not in repr(settings)
