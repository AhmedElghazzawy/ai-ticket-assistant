"""Settings: checked at startup, clear errors, and the API key never printed."""

import pytest
from pydantic import ValidationError

from config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test with no Gemini variables, whatever is set on this computer."""
    for name in ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)


def load(monkeypatch: pytest.MonkeyPatch, **values: str) -> Settings:
    """Settings from the given variables only; _env_file=None so the real .env is never read."""
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_reads_settings_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, GEMINI_API_KEY="test-key", GEMINI_MODEL="test-model")
    assert settings.gemini_model == "test-model"
    assert settings.gemini_api_key.get_secret_value() == "test-key"
    assert settings.gemini_timeout_seconds == 60


def test_missing_key_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="gemini_api_key"):
        load(monkeypatch, GEMINI_MODEL="test-model")


def test_wrong_timeout_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError, match="gemini_timeout_seconds"):
        load(monkeypatch, GEMINI_API_KEY="k", GEMINI_MODEL="m", GEMINI_TIMEOUT_SECONDS="-5")


def test_key_is_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, GEMINI_API_KEY="super-secret", GEMINI_MODEL="m")
    assert "super-secret" not in str(settings)
    assert "super-secret" not in repr(settings)
