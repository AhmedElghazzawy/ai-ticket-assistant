"""Demo mode: one click shows the staff console with sample tickets, never real visitors' data."""

import json

import pytest
from fakes import fake_result
from fastapi.testclient import TestClient

from helpdesk import auth
from helpdesk.api import app as api
from helpdesk.storage.tickets import DEMO_PATH

DEMO_COUNT = len(json.loads(DEMO_PATH.read_text(encoding="utf-8")))


@pytest.fixture
def demo_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "DEMO_MODE", True)


def browser() -> TestClient:
    return TestClient(api.app, base_url="https://testserver")


def real_visitor_ticket(monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(api, "process_ticket", lambda *args: fake_result(auto_send=False))
    response = browser().post("/api/tickets", json={"text": "my real problem", "language": "tr"})
    return int(response.json()["ticket_id"])


def test_demo_is_off_unless_enabled() -> None:
    assert browser().get("/api/auth/options").json() == {"demo": False}
    assert browser().post("/api/auth/demo").status_code == 404


def test_one_click_shows_the_sample_queue(demo_on: None) -> None:
    demo = browser()
    assert demo.get("/api/auth/options").json() == {"demo": True}
    me = demo.post("/api/auth/demo").json()
    assert me["demo"] is True and me["role"] == "admin"
    queue = demo.get("/api/staff/tickets").json()
    assert len(queue) == DEMO_COUNT and all(ticket["demo"] for ticket in queue)


def test_demo_never_sees_real_tickets_and_staff_never_see_demo_tickets(
    demo_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    number = real_visitor_ticket(monkeypatch)
    demo = browser()
    demo.post("/api/auth/demo")
    assert number not in [t["id"] for t in demo.get("/api/staff/tickets").json()]
    assert demo.get(f"/api/staff/tickets/{number}").status_code == 404

    with api.database() as db:
        auth.create_staff(db, "admin@bilecik.edu.tr", "Admin", "admin", None, "a long password!")
    admin = browser()
    admin.post(
        "/api/auth/login", json={"email": "admin@bilecik.edu.tr", "password": "a long password!"}
    )
    assert [t["id"] for t in admin.get("/api/staff/tickets").json()] == [number]


def test_the_demo_account_cannot_be_used_with_a_password(demo_on: None) -> None:
    browser().post("/api/auth/demo")  # creates the demo account
    with api.database() as db:
        row = db.execute("SELECT email FROM staff WHERE demo").fetchone()
        assert row is not None
        assert auth.authenticate(db, row["email"], "", ip="1.2.3.4") is None


def test_each_demo_login_starts_fresh(demo_on: None) -> None:
    demo = browser()
    demo.post("/api/auth/demo")
    first = demo.get("/api/staff/tickets").json()[0]["id"]
    demo.post(f"/api/staff/tickets/{first}/reply", json={"reply": "done"})
    assert len(demo.get("/api/staff/tickets").json()) == DEMO_COUNT - 1
    browser().post("/api/auth/demo")  # the next visitor
    assert len(demo.get("/api/staff/tickets").json()) == DEMO_COUNT


def test_demo_tickets_do_not_count_toward_the_daily_cap(
    demo_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    browser().post("/api/auth/demo")  # 16 demo tickets now exist
    monkeypatch.setattr(api, "DAILY_TICKET_CAP", 1)
    assert real_visitor_ticket(monkeypatch) > 0  # the one real ticket of the day is still allowed
