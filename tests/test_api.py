"""Tests for the web API. The real pipeline is replaced by a fake one, so no Gemini calls are made."""

import pytest
from fastapi.testclient import TestClient

import api
from answer import Answer
from classifier import Classification
from decision import Decision
from knowledge_base import Chunk
from pipeline import TicketResult

client = TestClient(api.app)
CHUNK = Chunk(id="harc_ucretler.tr#5", doc="harc_ucretler", language="tr", title="Katkı Payı ve İadeler",
              source="Öğrenci İşleri SSS", text="Kayıt sildirince iade\nGeri ödenmez.")


def fake_result(auto_send: bool, escalate: bool = False, priority: str = "low") -> TicketResult:
    """A hand-made pipeline result."""
    return TicketResult(
        classification=Classification(reason="test", category="billing", priority=priority, escalate=escalate),
        hits=[(0.8, CHUNK)],
        answer=Answer(evidence="Geri ödenmez.", covered=True, reply="SECRET DRAFT", sources=[CHUNK.id]),
        decision=Decision(auto_send=auto_send, reasons=[] if auto_send else ["test reason"]),
    )


def ask(text: str = "Harç iade edilir mi?", language: str = "tr"):
    return client.post("/api/tickets", json={"text": text, "language": language})


def test_page_and_files_are_served():
    for path in ("/", "/static/style.css", "/static/app.js"):
        assert client.get(path).status_code == 200


def test_empty_text_is_rejected():
    assert ask(text="").status_code == 422


def test_unknown_language_is_rejected():
    assert ask(language="de").status_code == 422


def test_forwarded_ticket_never_shows_the_draft(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    response = ask()
    assert response.status_code == 200
    assert response.json()["reply"] is None
    assert response.json()["sources"] == []
    assert "SECRET DRAFT" not in response.text  # not even hidden somewhere in the response


def test_auto_sent_answer_has_reply_and_source(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=True))
    body = ask().json()
    assert body["reply"] == "SECRET DRAFT"
    assert body["sources"] == [{"title": "Katkı Payı ve İadeler", "section": "Kayıt sildirince iade"}]
    assert body["office"] == "Öğrenci İşleri, İstatistik Disiplin ve Harçlar Şube Müdürlüğü"


def test_urgent_escalation_shows_emergency(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(False, escalate=True, priority="urgent"))
    assert ask().json()["emergency"] is True


def test_errors_do_not_leak_internal_details(monkeypatch: pytest.MonkeyPatch):
    def broken(*args):
        raise RuntimeError("internal secret details")
    monkeypatch.setattr(api, "process_ticket", broken)
    response = ask()
    assert response.status_code == 503
    assert "internal secret details" not in response.text
