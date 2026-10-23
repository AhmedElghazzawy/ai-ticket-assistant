"""Tests for the staff statistics: hand-made tickets, no database, no AI calls."""

from datetime import UTC, datetime, timedelta
from typing import Any

from decision import SimpleReason, WeakMatch
from insights import summarize
from store import StoredTicket

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def ticket(**changes: Any) -> StoredTicket:
    base: dict[str, Any] = {
        "id": 1,
        "created_at": NOW - timedelta(hours=1),
        "language": "tr",
        "text": "t",
        "category": "billing",
        "priority": "low",
        "escalate": False,
        "ai_reason": "r",
        "office": "fees",
        "auto_send": False,
        "reasons": [SimpleReason(code="not_covered")],
        "top_score": 0.8,
        "draft": "d",
        "covered": False,
        "sources": [],
        "status": "open",
        "final_reply": None,
        "handled_at": None,
        "demo": False,
    }
    return StoredTicket(**(base | changes))


TICKETS = [
    ticket(id=1, status="auto_sent", auto_send=True, reasons=[], feedback="helpful"),
    ticket(id=2),  # open, first help (not_covered only)
    ticket(id=3, reasons=[SimpleReason(code="escalation")], category="other"),  # open, no help
    ticket(
        id=4,
        status="handled",
        reasons=[WeakMatch(score=0.5, min=0.65)],
        handled_at=NOW - timedelta(days=2, minutes=30),  # answered 30 minutes after it arrived
        feedback="not_helpful",
        created_at=NOW - timedelta(days=2, hours=1),
    ),
]


def test_outcomes_split_every_ticket_exactly_once() -> None:
    s = summarize(TICKETS, NOW)
    assert s.total == 4
    assert s.outcomes.model_dump() == {
        "auto_sent": 1,
        "first_help_waiting": 1,
        "waiting": 1,
        "handled": 1,
    }


def test_reply_time_and_feedback_with_their_sample_size() -> None:
    s = summarize(TICKETS, NOW)
    assert s.median_reply_minutes == 30.0
    assert s.handled_n == 1
    assert (s.feedback_helpful, s.feedback_n) == (1, 2)


def test_every_category_is_listed_even_with_zero_tickets() -> None:
    counts = summarize(TICKETS, NOW).by_category
    assert counts["billing"] == 3 and counts["other"] == 1 and counts["it_support"] == 0
    assert len(counts) == 7


def test_last_14_days_by_day_including_empty_days() -> None:
    days = summarize(TICKETS, NOW).by_day
    assert len(days) == 14
    assert days[-1].day == NOW.date() and days[-1].count == 3
    assert days[-3].count == 1  # the ticket from two days ago


def test_no_tickets_gives_zeros_not_errors() -> None:
    s = summarize([], NOW)
    assert s.total == 0 and s.median_reply_minutes is None and s.feedback_n == 0


def test_first_help_counts_tickets_that_staff_answered_later_too() -> None:
    later = ticket(id=5, status="handled", handled_at=NOW)  # first help, then a staff reply
    s = summarize([*TICKETS, later], NOW)
    assert s.outcomes.handled == 2
    assert s.first_help_total == 2  # tickets 2 and 5: "helped right away" must count both
