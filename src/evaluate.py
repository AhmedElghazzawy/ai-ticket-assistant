"""Run the classifier on every labeled ticket, save the results and score them."""

import json
from datetime import datetime

from pydantic import BaseModel

from classifier import Classification
from tickets import PROJECT_ROOT, Ticket

RESULTS_FILE = PROJECT_ROOT / "eval" / "results.json"


class Result(BaseModel):
    """One ticket, with both the correct labels and what the model predicted."""
    ticket: Ticket
    prediction: Classification

    @property
    def category_ok(self) -> bool:
        return self.prediction.category == self.ticket.category

    @property
    def priority_ok(self) -> bool:
        return self.prediction.priority == self.ticket.priority

    @property
    def escalate_ok(self) -> bool:
        return self.prediction.escalate == self.ticket.escalate

    @property
    def all_ok(self) -> bool:
        return self.category_ok and self.priority_ok and self.escalate_ok


class EvalRun(BaseModel):
    """A full evaluation: which model, when it ran, and every result."""
    model: str
    finished_at: datetime
    results: list[Result]


def save_run(run: EvalRun) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(run.model_dump_json(indent=2))


def load_run() -> EvalRun | None:
    """Return the last saved run, or None if we have never run an evaluation."""
    if not RESULTS_FILE.exists():
        return None
    return EvalRun.model_validate_json(RESULTS_FILE.read_text())


def score(results: list[Result]) -> dict[str, float]:
    """Percentage of tickets the model got right, for each label and overall."""
    total = len(results)
    return {
        "category": 100 * sum(r.category_ok for r in results) / total,
        "priority": 100 * sum(r.priority_ok for r in results) / total,
        "escalate": 100 * sum(r.escalate_ok for r in results) / total,
        "all": 100 * sum(r.all_ok for r in results) / total,
    }


def missed_escalations(results: list[Result]) -> list[Result]:
    """Tickets that needed a human but the model did not escalate: the most dangerous mistake."""
    return [r for r in results if r.ticket.escalate and not r.prediction.escalate]
