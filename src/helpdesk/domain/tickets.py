"""What a valid ticket is, and how to load tickets.jsonl with clear errors."""

from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from helpdesk.core.paths import DATA_DIR

# A label typo ("billng") fails loudly instead of silently becoming a new class.
Category = Literal[
    "account_access",
    "it_support",
    "registration",
    "academic_records",
    "billing",
    "campus_life",
    "other",
]
Priority = Literal["low", "medium", "high", "urgent"]
Language = Literal["tr", "en"]

TICKETS_PATH = DATA_DIR / "tickets" / "tickets.jsonl"
# The two LOCKED sets (ADR 0003): measure only, never tune a prompt on them.
TEST_PATH = TICKETS_PATH.parent / "test_tickets.jsonl"
REALISTIC_PATH = (
    TICKETS_PATH.parent / "realistic_tickets.jsonl"
)  # typos, mixed TR/EN, several issues
DATASETS = {"dev": TICKETS_PATH, "test": TEST_PATH, "realistic": REALISTIC_PATH}


class Ticket(BaseModel):
    """One labeled support ticket."""

    # A misspelt field ("categroy") or a string "yes" for a bool would silently corrupt a score.
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    text: str = Field(min_length=1)
    language: Language
    category: Category
    priority: Priority
    escalate: bool


def load_tickets(path: Path = TICKETS_PATH) -> list[Ticket]:
    """Read one ticket per line. Stop with the line number if a line is invalid."""
    tickets = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue  # skip blank lines
        try:
            tickets.append(Ticket.model_validate_json(line))
        except ValidationError as error:
            raise ValueError(f"{path.name}, line {line_no}:\n{error}") from error

    ids = [t.id for t in tickets]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"{path.name}: duplicate ids {duplicates}")
    return tickets


def print_summary(tickets: list[Ticket]) -> None:
    """Show how the tickets are spread over languages and labels."""
    print(f"Valid tickets: {len(tickets)}")
    for field in ("language", "category", "priority", "escalate"):
        counts = Counter(getattr(t, field) for t in tickets)
        print(f"  {field}: {dict(sorted(counts.items(), key=str))}")


if __name__ == "__main__":
    print_summary(load_tickets())
