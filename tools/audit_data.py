"""Audit the ticket data: what it covers and what is missing, before writing new tickets.

Read-only, no AI calls. Run: uv run python tools/audit_data.py
"""

import json
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tickets import TEST_PATH, TICKETS_PATH, Ticket, load_tickets  # noqa: E402

EXPECTED_PATH = TICKETS_PATH.parent / "expected_docs.jsonl"


def table(title: str, tickets: list[Ticket], row: Callable[[Ticket], str]) -> None:
    """Count tickets per row value, split by language (tr / en / all)."""
    counts = Counter((row(t), t.language) for t in tickets)
    print(f"\n{title}")
    print(f"  {'':18} {'tr':>4} {'en':>4} {'all':>5}")
    for value in sorted({row(t) for t in tickets}):
        tr, en = counts[(value, "tr")], counts[(value, "en")]
        print(f"  {value:18} {tr:>4} {en:>4} {tr + en:>5}")


TURKISH_LETTERS = set("çğıöşüÇĞİÖŞÜ")
# A few very common English words; a Turkish ticket containing them is probably mixed TR/EN.
ENGLISH_WORDS = {
    "password",
    "login",
    "deadline",
    "course",
    "exam",
    "email",
    "please",
    "help",
    "the",
    "free",
}
INJECTION_WORDS = ("ignore", "system:", "override", "talimat", "kuralları unut")

# Simple text rules: they ESTIMATE hard cases. Typos and "two problems in one ticket" cannot be
# found reliably by a rule, so those are counted by reading the tickets, not here.
HARD_CASES: dict[str, Callable[[Ticket], bool]] = {
    "very short (<40 chars)": lambda t: len(t.text) < 40,
    "long (>300 chars)": lambda t: len(t.text) > 300,
    "TR without Turkish letters": lambda t: (
        t.language == "tr" and not TURKISH_LETTERS & set(t.text)
    ),
    "TR with English words": lambda t: (
        t.language == "tr" and bool(ENGLISH_WORDS & set(t.text.lower().split()))
    ),
    "EN with Turkish letters": lambda t: t.language == "en" and bool(TURKISH_LETTERS & set(t.text)),
    "injection attempt": lambda t: any(w in t.text.lower() for w in INJECTION_WORDS),
}


def hard_cases(tickets: list[Ticket]) -> None:
    """Text length and how many tickets look like each hard case (by language)."""
    lengths = sorted(len(t.text) for t in tickets)
    print(
        f"\nlength in characters: min {lengths[0]}, median {lengths[len(lengths) // 2]}, max {lengths[-1]}"
    )
    print(f"\nhard cases (estimated by simple rules)\n  {'':28} {'tr':>4} {'en':>4}")
    for name, rule in HARD_CASES.items():
        hits = [t for t in tickets if rule(t)]
        tr = sum(t.language == "tr" for t in hits)
        print(f"  {name:28} {tr:>4} {len(hits) - tr:>4}")


def main() -> None:
    expected = {
        r["id"]: r["doc"]
        for r in map(json.loads, EXPECTED_PATH.read_text(encoding="utf-8").splitlines())
    }
    for name, path in (("DEV", TICKETS_PATH), ("LOCKED TEST", TEST_PATH)):
        tickets = load_tickets(path)
        print(f"\n===== {name}: {len(tickets)} tickets =====")
        table("category", tickets, lambda t: t.category)
        table("priority", tickets, lambda t: t.priority)
        table("escalate", tickets, lambda t: str(t.escalate))
        table("answered by a document", tickets, lambda t: str(expected[t.id] != "none"))
        hard_cases(tickets)


if __name__ == "__main__":
    main()
