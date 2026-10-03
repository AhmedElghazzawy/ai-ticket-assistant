"""Load and validate the labeled sample tickets in data/tickets/tickets.jsonl."""

from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# Paths are built from this file's location, so the script works from any folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TICKETS_FILE = PROJECT_ROOT / "data" / "tickets" / "tickets.jsonl"

# The only allowed values. A typo like "biling" in the data becomes an error, not a silent bug
Category = Literal[
    "account_access", "registration", "billing", "it_support",
    "academic_records", "housing", "other",
]
Priority = Literal["low", "medium", "high", "urgent"]


class Ticket(BaseModel):
    id: str
    text: str
    category: Category
    priority: Priority
    escalate: bool


def load_tickets(path: Path = TICKETS_FILE) -> list[Ticket]:
    """Read one JSON object per line and validate each into a Ticket."""
    tickets = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if line.strip():
            try:
                tickets.append(Ticket.model_validate_json(line))
            except ValueError as error:
                raise ValueError(f"{path.name} line {line_number}: {error}") from error
    return tickets


if __name__ == "__main__":
    tickets = load_tickets()
    print(f"Loaded {len(tickets)} valid tickets\n")
    print("By category:", dict(Counter(t.category for t in tickets)))
    print("By priority:", dict(Counter(t.priority for t in tickets)))
    print("Escalate:   ", dict(Counter(t.escalate for t in tickets)))
