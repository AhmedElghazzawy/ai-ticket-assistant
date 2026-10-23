"""Tests for the web API. The real pipeline is replaced by a fake one, so no Gemini calls are made."""

import hashlib
from pathlib import Path
from typing import NoReturn

import httpx2
import pytest
from fakes import CHUNK, fake_result
from fastapi.testclient import TestClient

import api
import auth
from auth import Role
from decision import MIN_SCORE, OfficeId, SimpleReason
from pipeline import TicketResult

client = TestClient(api.app)


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


# Stress tests (Phase 11): bad input is refused BEFORE any Gemini call is paid for.
def count_pipeline_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def fake(text: str, *args: object) -> TicketResult:
        calls.append(text)
        return fake_result(auto_send=False)

    monkeypatch.setattr(api, "process_ticket", fake)
    return calls


@pytest.mark.parametrize("text", ["   ", "\n\t \n", "\u3000"])  # spaces, newlines, wide space
def test_blank_text_is_rejected_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    calls = count_pipeline_calls(monkeypatch)
    assert ask(text=text).status_code == 422
    assert calls == []


def test_text_length_limit_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = count_pipeline_calls(monkeypatch)
    assert ask(text="a" * 2000).status_code == 200
    assert ask(text="a" * 2001).status_code == 422
    assert len(calls) == 1


def test_nul_character_is_rejected_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Postgres cannot store NUL in text: without this check, the model would run, then saving fails.
    calls = count_pipeline_calls(monkeypatch)
    assert ask(text="Harç\x00 iade").status_code == 422
    assert calls == []


def test_text_is_trimmed_before_the_model_sees_it(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = count_pipeline_calls(monkeypatch)
    ask(text="  Harç iade edilir mi?\n")
    assert calls == ["Harç iade edilir mi?"]


def test_html_in_a_ticket_stays_plain_text_for_staff(monkeypatch: pytest.MonkeyPatch) -> None:
    attack = "<script>alert('x')</script><img src=x onerror=alert(1)> Harç?"
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    ask(text=attack)
    queue = staff_client().get("/api/staff/tickets").json()
    assert queue[0]["text"] == attack  # exact text as data; the page shows it as text, never HTML


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
            "source": "Öğrenci İşleri SSS",  # shown on the card (e.g. "Resmî olmayan kaynak: ...")
            "url": CHUNK.url,
        }
    ]
    assert body["office"] == "fees"  # an ID: the page shows the name in the student's language


def test_partly_answered_ticket_shows_first_help(monkeypatch: pytest.MonkeyPatch) -> None:
    # Forwarded because the documents answer only part: the cited part helps the student now.
    partly = fake_result(False, forward_reason=SimpleReason(code="not_covered"))
    monkeypatch.setattr(api, "process_ticket", lambda *args: partly)
    body = ask().json()
    assert body["auto_send"] is False
    assert body["first_help"] is True
    assert body["reply"] == "SECRET DRAFT"
    assert [source["id"] for source in body["sources"]] == [CHUNK.id]


def test_answer_explains_how_it_was_decided(monkeypatch: pytest.MonkeyPatch) -> None:
    # "Nasıl karar verildi?": reason codes and the match score, never the draft or model text.
    partly = fake_result(False, forward_reason=SimpleReason(code="not_covered"))
    monkeypatch.setattr(api, "process_ticket", lambda *args: partly)
    body = ask().json()
    assert body["reasons"] == [{"code": "not_covered"}]
    assert body["top_score"] == 0.8 and body["min_score"] == MIN_SCORE
    assert "ai_reason" not in body  # the model's own explanation stays with staff


def test_escalated_ticket_shows_no_first_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(False, escalate=True))
    body = ask().json()
    assert body["first_help"] is False
    assert body["reply"] is None


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

PASSWORD = "correct horse battery"


def staff_client(role: Role = "admin", office: OfficeId | None = None) -> TestClient:
    """A browser logged in as a new staff member (https, so the Secure cookie is sent back)."""
    email = f"{role}-{office}@bilecik.edu.tr"
    with api.database() as db:
        auth.create_staff(db, email, "Test", role, office, PASSWORD)
    browser = TestClient(api.app, base_url="https://testserver")
    assert browser.post("/api/auth/login", json={"email": email, "password": PASSWORD}).is_success
    return browser


def forwarded_ticket(monkeypatch: pytest.MonkeyPatch) -> int:
    """A student sends a ticket that is forwarded (a billing ticket: office "fees")."""
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    return int(ask().json()["ticket_id"])


def test_staff_pages_need_a_login(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    for response in (
        client.get("/api/staff/tickets"),
        client.get(f"/api/staff/tickets/{number}"),
        client.post(f"/api/staff/tickets/{number}/reply", json={"reply": "x"}),
        client.get("/api/auth/me"),
    ):
        assert response.status_code == 401
        assert "Harç" not in response.text  # no student data without a login


def test_login_sets_a_safe_cookie_and_me_returns_the_staff_member() -> None:
    browser = staff_client("staff", "fees")
    response = browser.post(
        "/api/auth/login", json={"email": "staff-fees@bilecik.edu.tr", "password": PASSWORD}
    )
    cookie = response.headers["set-cookie"]  # exactly what the browser receives
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api"):
        assert flag in cookie
    assert browser.get("/api/auth/me").json()["office"] == "fees"


def test_wrong_password_and_unknown_email_get_the_same_answer() -> None:
    staff_client("staff", "fees")
    wrong = client.post(
        "/api/auth/login", json={"email": "staff-fees@bilecik.edu.tr", "password": "nope"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "no@bilecik.edu.tr", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # nobody learns which emails exist


def test_too_many_wrong_passwords_are_slowed_down() -> None:
    staff_client("staff", "fees")
    body = {"email": "staff-fees@bilecik.edu.tr", "password": "wrong guess"}
    codes = [client.post("/api/auth/login", json=body).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_logout_ends_the_session() -> None:
    browser = staff_client()
    assert browser.post("/api/auth/logout").is_success
    assert browser.get("/api/auth/me").status_code == 401


def test_staff_see_only_their_office_and_admins_see_all(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)  # office "fees"
    fees, it, admin = staff_client("staff", "fees"), staff_client("staff", "it"), staff_client()
    assert [t["id"] for t in fees.get("/api/staff/tickets").json()] == [number]
    assert it.get("/api/staff/tickets").json() == []
    assert it.get(f"/api/staff/tickets/{number}").status_code == 404  # hidden, not "forbidden"
    assert it.post(f"/api/staff/tickets/{number}/reply", json={"reply": "x"}).status_code == 404
    assert [t["id"] for t in admin.get("/api/staff/tickets").json()] == [number]


def test_changes_from_another_website_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    browser = staff_client()
    evil = browser.post(
        f"/api/staff/tickets/{number}/reply",
        json={"reply": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert evil.status_code == 403  # CSRF: the staff member's cookie must not work for them
    same = browser.post(
        f"/api/staff/tickets/{number}/reply",
        json={"reply": "ok"},
        headers={"Origin": "https://testserver"},
    )
    assert same.is_success


def test_staff_queue_lists_open_tickets_with_the_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    [ticket] = staff_client().get("/api/staff/tickets").json()
    assert ticket["id"] == number and ticket["status"] == "open"
    assert ticket["draft"] == "SECRET DRAFT"  # staff DO see the draft (students never do)
    assert ticket["reasons"] == [{"code": "escalation"}]


def test_unknown_ticket_numbers_give_404(monkeypatch: pytest.MonkeyPatch) -> None:
    assert staff_client().get("/api/staff/tickets/999").status_code == 404


def test_reply_closes_the_ticket_and_a_second_reply_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    number = forwarded_ticket(monkeypatch)
    browser = staff_client()
    sent = browser.post(f"/api/staff/tickets/{number}/reply", json={"reply": "  Merhaba.  "})
    assert sent.json()["status"] == "handled" and sent.json()["final_reply"] == "Merhaba."
    assert browser.get("/api/staff/tickets").json() == []  # out of the queue
    again = browser.post(f"/api/staff/tickets/{number}/reply", json={"reply": "Again"})
    assert again.status_code == 409  # two staff members cannot both answer one ticket


def test_empty_reply_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    response = staff_client().post(f"/api/staff/tickets/{number}/reply", json={"reply": ""})
    assert response.status_code == 422


def test_reassign_accepts_only_real_offices(monkeypatch: pytest.MonkeyPatch) -> None:
    number = forwarded_ticket(monkeypatch)
    browser = staff_client()
    moved = browser.patch(f"/api/staff/tickets/{number}", json={"office": "student_affairs"})
    assert moved.json()["office"] == "student_affairs"
    wrong = browser.patch(f"/api/staff/tickets/{number}", json={"office": "rectorate"})
    assert wrong.status_code == 422


def test_health_check_answers_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


# ---------------------------------------------------------------- abuse protection


@pytest.fixture
def fresh_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fake, cheap pipeline (conftest.py already gives every test empty counters)."""
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))


def test_one_visitor_gets_at_most_5_tickets_a_minute(fresh_limits: None) -> None:
    codes = [ask().status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]


def test_the_limit_is_per_visitor(fresh_limits: None) -> None:
    for _ in range(5):
        ask()
    other = TestClient(api.app, client=("203.0.113.9", 50000))  # another visitor
    assert other.post("/api/tickets", json={"text": "Merhaba", "language": "tr"}).is_success


def test_the_whole_system_has_a_daily_cap(
    fresh_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api, "DAILY_TICKET_CAP", 2)
    visitors = [TestClient(api.app, client=(f"203.0.113.{n}", 50000)) for n in range(3)]
    body = {"text": "Merhaba", "language": "tr"}
    codes = [v.post("/api/tickets", json=body).status_code for v in visitors]
    assert codes == [200, 200, 429]  # different visitors, same daily ceiling


def test_a_blocked_request_costs_nothing(
    fresh_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def counting_pipeline(*args: object) -> TicketResult:
        calls.append(1)
        return fake_result(auto_send=False)

    monkeypatch.setattr(api, "process_ticket", counting_pipeline)
    for _ in range(7):
        ask()
    assert len(calls) == 5  # the pipeline (Gemini) never ran for the refused requests


def test_a_faked_ip_header_is_ignored_unless_a_proxy_is_configured(fresh_limits: None) -> None:
    # Without CLIENT_IP_HEADER, a bot sending a new fake address each time must still be limited.
    codes = [
        client.post(
            "/api/tickets",
            json={"text": "Merhaba", "language": "tr"},
            headers={"CF-Connecting-IP": f"198.51.100.{n}"},
        ).status_code
        for n in range(6)
    ]
    assert codes == [200] * 5 + [429]


def test_behind_a_trusted_proxy_each_real_visitor_has_its_own_limit(
    fresh_limits: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On Render every request comes through Cloudflare; the real visitor is in CF-Connecting-IP.
    monkeypatch.setattr(api, "CLIENT_IP_HEADER", "cf-connecting-ip")
    body = {"text": "Merhaba", "language": "tr"}
    for _ in range(5):
        client.post("/api/tickets", json=body, headers={"CF-Connecting-IP": "198.51.100.1"})
    other = client.post("/api/tickets", json=body, headers={"CF-Connecting-IP": "198.51.100.2"})
    assert other.is_success  # same proxy address, different real visitor
    same = client.post("/api/tickets", json=body, headers={"CF-Connecting-IP": "198.51.100.1"})
    assert same.status_code == 429


# ---------------------------------------------------------------- student: status and feedback


def lookup(ticket_id: int, code: str) -> httpx2.Response:
    # POST, not a URL: the secret code never appears in server logs
    return client.post("/api/tickets/lookup", json={"ticket_id": ticket_id, "code": code})


def test_new_ticket_gets_a_secret_code_and_only_its_hash_is_stored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    body = ask().json()
    code = body["access_code"]
    assert len(code) >= 20  # 128+ random bits: impossible to guess
    with api.database() as db:
        row = db.execute(
            "SELECT access_hash FROM tickets WHERE id = %s", (body["ticket_id"],)
        ).fetchone()
    assert row is not None
    assert row["access_hash"] == hashlib.sha256(code.encode()).hexdigest()  # never the code itself


def test_student_sees_the_status_and_then_the_staff_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    body = ask().json()
    number, code = body["ticket_id"], body["access_code"]
    first = lookup(number, code).json()
    assert first["status"] == "open" and first["reply"] is None
    assert "SECRET DRAFT" not in lookup(number, code).text  # the unchecked draft stays private
    staff_client().post(f"/api/staff/tickets/{number}/reply", json={"reply": "Dilekçe verin."})
    later = lookup(number, code).json()
    assert later["status"] == "handled" and later["reply"] == "Dilekçe verin."


def test_auto_sent_ticket_shows_its_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=True))
    body = ask().json()
    found = lookup(body["ticket_id"], body["access_code"]).json()
    assert found["status"] == "auto_sent" and found["reply"] == "SECRET DRAFT"


def test_wrong_code_and_unknown_ticket_look_exactly_the_same(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    body = ask().json()
    wrong_code = lookup(body["ticket_id"], "x" * 22)
    unknown_ticket = lookup(body["ticket_id"] + 1000, body["access_code"])
    assert wrong_code.status_code == unknown_ticket.status_code == 404
    assert wrong_code.json() == unknown_ticket.json()  # nobody can probe which numbers exist


def test_feedback_needs_the_code_and_the_last_choice_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=True))
    body = ask().json()
    number, code = body["ticket_id"], body["access_code"]
    url = f"/api/tickets/{number}/feedback"
    assert client.post(url, json={"code": "x" * 22, "helpful": True}).status_code == 404
    assert client.post(url, json={"code": code, "helpful": True}).status_code == 204
    assert client.post(url, json={"code": code, "helpful": False}).status_code == 204
    with api.database() as db:
        row = db.execute("SELECT feedback FROM tickets WHERE id = %s", (number,)).fetchone()
    assert row is not None and row["feedback"] == "not_helpful"


def test_lookups_are_rate_limited_per_visitor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "lookup_limiter", api.RateLimiter(((3, 60.0),)))
    answers = [lookup(1, "x" * 22).status_code for _ in range(4)]
    assert answers == [404, 404, 404, 429]  # free to answer, but not unlimited
