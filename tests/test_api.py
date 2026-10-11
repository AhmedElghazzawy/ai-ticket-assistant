"""Tests for the web API. The real pipeline is replaced by a fake one, so no Gemini calls are made."""

from pathlib import Path
from typing import NoReturn

import httpx2
import pytest
from fastapi.testclient import TestClient

import api
from answer import Answer
from classifier import Classification
from decision import Decision, SimpleReason
from knowledge_base import Chunk
from pipeline import TicketResult
from tickets import Priority

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def temporary_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every API test writes to its own temporary database, never to the real one."""
    monkeypatch.setattr(api, "DB_FILE", tmp_path / "test.db")


CHUNK = Chunk(
    id="harc_ucretler.tr#5",
    doc="harc_ucretler",
    language="tr",
    title="Katkı Payı ve İadeler",
    source="Öğrenci İşleri SSS",
    url="https://bilecik.edu.tr/ogrenciisleri/Icerik/HARc_isLEMLERi",
    text="Kayıt sildirince iade\nGeri ödenmez.",
)


def fake_result(
    auto_send: bool, escalate: bool = False, priority: Priority = "low"
) -> TicketResult:
    """A hand-made pipeline result."""
    return TicketResult(
        classification=Classification(
            reason="test", category="billing", priority=priority, escalate=escalate
        ),
        hits=[(0.8, CHUNK)],
        answer=Answer(
            evidence="Geri ödenmez.", covered=True, reply="SECRET DRAFT", sources=[CHUNK.id]
        ),
        decision=Decision(
            auto_send=auto_send, reasons=[] if auto_send else [SimpleReason(code="escalation")]
        ),
    )


def ask(text: str = "Harç iade edilir mi?", language: str = "tr") -> httpx2.Response:
    return client.post("/api/tickets", json={"text": text, "language": language})


@pytest.fixture
def built_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tiny fake frontend build, so these tests do not need npm."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>APP</html>")
    (dist / "assets" / "app.js").write_text("console.log('js')")
    (tmp_path / ".env").write_text("GEMINI_API_KEY=secret")  # next to dist, like the real one
    monkeypatch.setattr(api, "DIST_DIR", dist)
    return dist


def test_app_files_are_served(built_app: Path) -> None:
    assert client.get("/").text == "<html>APP</html>"
    assert client.get("/assets/app.js").text == "console.log('js')"


def test_app_addresses_get_the_app_so_its_router_can_pick_the_page(built_app: Path) -> None:
    assert client.get("/staff/tickets/2").text == "<html>APP</html>"


def test_unknown_api_address_is_a_404_not_the_app(built_app: Path) -> None:
    response = client.get("/api/nope")
    assert response.status_code == 404 and "APP" not in response.text


def test_path_traversal_cannot_read_files_outside_the_app(built_app: Path) -> None:
    for path in ("/../.env", "/%2e%2e/.env", "/assets/../../.env"):
        assert "secret" not in client.get(path).text


def test_empty_text_is_rejected() -> None:
    assert ask(text="").status_code == 422


def test_unknown_language_is_rejected() -> None:
    assert ask(language="de").status_code == 422


def test_forwarded_ticket_never_shows_the_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    response = ask()
    assert response.status_code == 200
    assert response.json()["reply"] is None
    assert response.json()["sources"] == []
    assert "SECRET DRAFT" not in response.text  # not even hidden somewhere in the response


def test_auto_sent_answer_has_reply_and_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=True))
    body = ask().json()
    assert body["reply"] == "SECRET DRAFT"
    assert body["sources"] == [
        {
            "id": CHUNK.id,
            "title": "Katkı Payı ve İadeler",
            "section": "Kayıt sildirince iade",
            "url": CHUNK.url,
        }
    ]
    assert body["office"] == "fees"  # an ID: the page shows the name in the student's language


def test_urgent_escalation_shows_emergency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api, "process_ticket", lambda *args: fake_result(False, escalate=True, priority="urgent")
    )
    assert ask().json()["emergency"] is True


def test_errors_do_not_leak_internal_details(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object) -> NoReturn:
        raise RuntimeError("internal secret details")

    monkeypatch.setattr(api, "process_ticket", broken)
    response = ask()
    assert response.status_code == 503
    assert "internal secret details" not in response.text


def test_every_ticket_gets_a_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    first, second = ask().json()["ticket_id"], ask().json()["ticket_id"]
    assert second == first + 1


# ---------------------------------------------------------------- staff console


def forwarded_ticket(monkeypatch: pytest.MonkeyPatch) -> int:
    """A student sends a ticket that is forwarded; returns its number."""
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    return int(ask().json()["ticket_id"])


def test_staff_queue_lists_open_tickets_with_the_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    [ticket] = client.get("/api/staff/tickets").json()
    assert ticket["id"] == number and ticket["status"] == "open"
    assert ticket["draft"] == "SECRET DRAFT"  # staff DO see the draft (students never do)
    assert ticket["reasons"] == [{"code": "escalation"}]


def test_staff_can_open_one_ticket_and_unknown_numbers_give_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    number = forwarded_ticket(monkeypatch)
    assert client.get(f"/api/staff/tickets/{number}").json()["office"] == "fees"
    assert client.get("/api/staff/tickets/999").status_code == 404


def test_reply_closes_the_ticket_and_a_second_reply_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    number = forwarded_ticket(monkeypatch)
    sent = client.post(f"/api/staff/tickets/{number}/reply", json={"reply": "  Merhaba.  "})
    assert sent.json()["status"] == "handled" and sent.json()["final_reply"] == "Merhaba."
    assert client.get("/api/staff/tickets").json() == []  # out of the queue
    again = client.post(f"/api/staff/tickets/{number}/reply", json={"reply": "Again"})
    assert again.status_code == 409  # two staff members cannot both answer one ticket


def test_empty_reply_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    assert client.post(f"/api/staff/tickets/{number}/reply", json={"reply": ""}).status_code == 422


def test_reassign_accepts_only_real_offices(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    moved = client.patch(f"/api/staff/tickets/{number}", json={"office": "student_affairs"})
    assert moved.json()["office"] == "student_affairs"
    wrong = client.patch(f"/api/staff/tickets/{number}", json={"office": "rectorate"})
    assert wrong.status_code == 422


def test_staff_pages_refuse_requests_from_other_computers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_ticket(monkeypatch)
    outsider = TestClient(api.app, client=("203.0.113.7", 50000))  # a documentation-only address
    assert outsider.get("/api/staff/tickets").status_code == 403
    assert outsider.post("/api/staff/tickets/1/reply", json={"reply": "x"}).status_code == 403
    assert "Harç" not in outsider.get("/api/staff/tickets").text  # no student data leaks
