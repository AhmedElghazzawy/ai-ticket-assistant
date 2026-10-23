"""Staff statistics (the Insights page): how tickets end, how fast staff reply, what students think.

Pure functions over saved tickets, so they are tested without a database. Every rate is shown
with its sample size on the page, because these numbers come from small samples."""

from collections import Counter
from datetime import date, datetime, timedelta
from statistics import median
from typing import get_args

from pydantic import BaseModel

from decision import Decision, show_first_help
from store import StoredTicket
from tickets import Category

DAYS = 14  # the trend chart's window


class Outcomes(BaseModel):
    """Every ticket counted exactly once (the stacked bar adds up to the total)."""

    auto_sent: int  # answered by the system, no person needed
    first_help_waiting: int  # forwarded, the student got first help, staff have not replied yet
    waiting: int  # forwarded, no first help, staff have not replied yet
    handled: int  # staff replied


class DayCount(BaseModel):
    day: date
    count: int


class Insights(BaseModel):
    total: int
    outcomes: Outcomes
    first_help_total: int  # every ticket that got first help, also those staff answered later
    median_reply_minutes: float | None  # None until staff have replied to at least one ticket
    handled_n: int  # the sample size of the reply time
    feedback_helpful: int
    feedback_n: int  # tickets with a thumbs up or down
    by_category: dict[Category, int]
    by_day: list[DayCount]  # the last DAYS days (UTC), oldest first, empty days included


def got_first_help(ticket: StoredTicket) -> bool:
    return show_first_help(Decision(auto_send=ticket.auto_send, reasons=ticket.reasons))


def summarize(tickets: list[StoredTicket], now: datetime) -> Insights:
    """All the numbers of the Insights page for these tickets."""
    open_tickets = [t for t in tickets if t.status == "open"]
    handled = [t for t in tickets if t.status == "handled" and t.handled_at is not None]
    minutes = [(t.handled_at - t.created_at).total_seconds() / 60 for t in handled if t.handled_at]
    rated = [t for t in tickets if t.feedback is not None]
    per_day = Counter(t.created_at.date() for t in tickets)
    today = now.date()
    categories = Counter(t.category for t in tickets)
    return Insights(
        total=len(tickets),
        outcomes=Outcomes(
            auto_sent=sum(t.status == "auto_sent" for t in tickets),
            first_help_waiting=sum(got_first_help(t) for t in open_tickets),
            waiting=sum(not got_first_help(t) for t in open_tickets),
            handled=sum(t.status == "handled" for t in tickets),
        ),
        first_help_total=sum(not t.auto_send and got_first_help(t) for t in tickets),
        median_reply_minutes=round(median(minutes), 1) if minutes else None,
        handled_n=len(minutes),
        feedback_helpful=sum(t.feedback == "helpful" for t in rated),
        feedback_n=len(rated),
        by_category={c: categories[c] for c in get_args(Category)},
        by_day=[
            DayCount(day=day, count=per_day[day])
            for day in (today - timedelta(days=n) for n in range(DAYS - 1, -1, -1))
        ],
    )
