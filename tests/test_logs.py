"""Logs: useful fields for every ticket, a request ID, and NEVER the student's words."""

import json
import os
import subprocess
import sys
from collections.abc import MutableMapping
from typing import Any, NoReturn

import pytest
from fakes import fake_result
from google.genai import types
from harness import Api
from structlog.testing import capture_logs

from helpdesk.ai import gemini
from helpdesk.ai.gemini import estimated_cost
from helpdesk.core.settings import GeminiSettings

SECRET = "Benim adım Ayşe Yılmaz, TC 12345678901, harç iade edilir mi?"  # personal data


def send(api: Api, **headers: str) -> tuple[list[MutableMapping[str, Any]], str]:
    """Send SECRET through the API (fake pipeline); return the log entries and the request ID."""
    api.use_pipeline(lambda *args: fake_result(auto_send=False))
    with capture_logs() as logs:
        response = api.ask(SECRET, headers=headers)
    return logs, response.headers["x-request-id"]


def test_ticket_created_has_the_decision_but_not_the_text(api: Api) -> None:
    logs, _ = send(api)
    [created] = [entry for entry in logs if entry["event"] == "ticket_created"]
    assert created["auto_send"] is False and created["reasons"] == ["escalation"]
    assert created["office"] == "fees" and created["text_length"] == len(SECRET)
    assert all("Ayşe" not in str(entry) and "12345678901" not in str(entry) for entry in logs)


def test_every_request_gets_an_id(api: Api) -> None:
    logs, request_id = send(api)
    [request] = [entry for entry in logs if entry["event"] == "request"]
    assert request["status"] == 200 and request["path"] == "/api/tickets"
    assert len(request_id) == 12


def test_a_safe_incoming_request_id_is_kept_and_an_unsafe_one_replaced(
    api: Api,
) -> None:
    assert send(api, **{"X-Request-ID": "abc-123"})[1] == "abc-123"
    unsafe = 'x FAKE LOG LINE {"event": "hacked"}'  # an attempt to forge log content
    replaced = send(api, **{"X-Request-ID": unsafe})[1]
    assert replaced != unsafe and len(replaced) == 12  # our own ID instead


def test_a_crash_logs_the_error_type_but_not_its_message(api: Api) -> None:
    def broken(*args: object) -> NoReturn:
        raise ValueError(f"model output echoed: {SECRET}")

    api.use_pipeline(broken)
    with capture_logs() as logs:
        api.ask(SECRET)
    [failed] = [entry for entry in logs if entry["event"] == "pipeline_failed"]
    assert failed["error_type"] == "ValueError"
    assert all("Ayşe" not in str(entry) for entry in logs)


def test_cost_estimate_uses_the_official_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(gemini, "get_gemini_settings", lambda: GeminiSettings(_env_file=None))
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=1000, candidates_token_count=200, thoughts_token_count=300
    )
    # 1000 input x $0.30/M + (200 output + 300 thinking) x $2.50/M = $0.00155
    assert estimated_cost(usage) == pytest.approx(0.00155)


def test_loggers_made_before_configure_still_write_json() -> None:
    # Bug we hit: llm.py and retrieval.py create their logger while being imported, before api.py
    # calls configure(); a non-lazy logger kept structlog's default (plain text) format.
    # A fresh Python process, so this test does not depend on what other tests configured.
    code = (
        "from helpdesk.core import logs; early = logs.get_logger('early'); logs.configure('json'); "
        "early.info('gemini_call', ms=1)"
    )
    env = {**os.environ, "LOG_FORMAT": "json", "PYTHONPATH": "src"}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    line = json.loads(result.stdout or result.stderr)
    assert line["event"] == "gemini_call" and line["module"] == "early"


def test_logging_is_configured_once_per_process() -> None:
    # Bug we hit while adding create_app: every new app reconfigured logging, and loggers already
    # in use kept the old configuration. The first call wins; later calls change nothing.
    code = (
        "from helpdesk.core import logs; logs.configure('json'); logs.configure('console'); "
        "logs.get_logger('x').info('second_call_ignored')"
    )
    env = {**os.environ, "PYTHONPATH": "src"}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert json.loads(result.stdout or result.stderr)["event"] == "second_call_ignored"
