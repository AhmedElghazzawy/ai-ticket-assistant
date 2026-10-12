"""Shared test setup, run automatically by pytest for every test."""

import pytest

import api


@pytest.fixture(autouse=True)
def fresh_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with empty per-visitor counters, so tests never limit each other."""
    monkeypatch.setattr(api, "ticket_limiter", api.RateLimiter())
