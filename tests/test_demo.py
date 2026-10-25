"""Demo mode: one click shows the staff console with sample tickets, never real visitors' data."""

import json
from collections.abc import Callable

import pytest
from fakes import fake_result
from harness import Api

from helpdesk import auth
from helpdesk.storage.tickets import DEMO_PATH

DEMO_COUNT = len(json.loads(DEMO_PATH.read_text(encoding="utf-8")))


@pytest.fixture
def demo(make_api: Callable[..., Api]) -> Api:
    """The public demo site: DEMO_MODE on."""
    return make_api(demo_mode=True)


def real_visitor_ticket(api: Api) -> int:
    api.use_pipeline(lambda *args: fake_result(auto_send=False))
    return int(api.ask("my real problem").json()["ticket_id"])


def test_demo_is_off_unless_enabled(api: Api) -> None:
    assert api.browser().get("/api/auth/options").json() == {"demo": False}
    assert api.browser().post("/api/auth/demo").status_code == 404


def test_one_click_shows_the_sample_queue(demo: Api) -> None:
    demo_browser = demo.browser()
    assert demo_browser.get("/api/auth/options").json() == {"demo": True}
    me = demo_browser.post("/api/auth/demo").json()
    assert me["demo"] is True and me["role"] == "admin"
    queue = demo_browser.get("/api/staff/tickets").json()
    assert len(queue) == DEMO_COUNT and all(ticket["demo"] for ticket in queue)


def test_demo_never_sees_real_tickets_and_staff_never_see_demo_tickets(demo: Api) -> None:
    number = real_visitor_ticket(demo)
    demo_browser = demo.browser()
    demo_browser.post("/api/auth/demo")
    assert number not in [t["id"] for t in demo_browser.get("/api/staff/tickets").json()]
    assert demo_browser.get(f"/api/staff/tickets/{number}").status_code == 404

    with demo.database() as db:
        auth.create_staff(db, "admin@bilecik.edu.tr", "Admin", "admin", None, "a long password!")
    admin = demo.browser()
    admin.post(
        "/api/auth/login", json={"email": "admin@bilecik.edu.tr", "password": "a long password!"}
    )
    assert [t["id"] for t in admin.get("/api/staff/tickets").json()] == [number]


def test_the_demo_account_cannot_be_used_with_a_password(demo: Api) -> None:
    demo.browser().post("/api/auth/demo")  # creates the demo account
    with demo.database() as db:
        row = db.execute("SELECT email FROM staff WHERE demo").fetchone()
        assert row is not None
        assert auth.authenticate(db, row["email"], "", ip="1.2.3.4") is None


def test_each_demo_login_starts_fresh(demo: Api) -> None:
    demo_browser = demo.browser()
    demo_browser.post("/api/auth/demo")
    first = demo_browser.get("/api/staff/tickets").json()[0]["id"]
    demo_browser.post(f"/api/staff/tickets/{first}/reply", json={"reply": "done"})
    assert len(demo_browser.get("/api/staff/tickets").json()) == DEMO_COUNT - 1
    demo.browser().post("/api/auth/demo")  # the next visitor
    assert len(demo_browser.get("/api/staff/tickets").json()) == DEMO_COUNT


def test_demo_tickets_do_not_count_toward_the_daily_cap(make_api: Callable[..., Api]) -> None:
    demo = make_api(demo_mode=True, daily_ticket_cap=1)
    demo.browser().post("/api/auth/demo")  # 16 demo tickets now exist
    assert real_visitor_ticket(demo) > 0  # the one real ticket of the day is still allowed
