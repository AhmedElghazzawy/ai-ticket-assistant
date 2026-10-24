"""The agent guardrail hook (.claude/hooks/guard_files.py): it must block every way of touching .env
or changing a locked test set, and let normal work through."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "guard_files.py"


def run_hook(tool: str, **tool_input: str) -> int:
    """Send one planned tool call to the hook, as Claude Code does; return its exit code."""
    call = json.dumps({"tool_name": tool, "tool_input": tool_input})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=call, capture_output=True, text=True, check=False
    ).returncode


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Read", {"file_path": "/repo/.env"}),
        ("Edit", {"file_path": "/repo/.env"}),
        ("Bash", {"command": "cat .env"}),
        ("Bash", {"command": "grep KEY ./.env"}),
        ("Edit", {"file_path": "/repo/data/tickets/test_tickets.jsonl"}),
        ("Write", {"file_path": "/repo/data/tickets/phase8_tickets.jsonl"}),
        ("Bash", {"command": "echo '{}' >> data/tickets/test_tickets.jsonl"}),
        ("Bash", {"command": "sed -i 's/low/high/' data/tickets/phase8_tickets.jsonl"}),
    ],
)
def test_blocked(tool: str, tool_input: dict[str, str]) -> None:
    assert run_hook(tool, **tool_input) == 2


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    [
        ("Read", {"file_path": "/repo/.env.example"}),
        ("Edit", {"file_path": "/repo/src/decision.py"}),
        ("Read", {"file_path": "/repo/data/tickets/test_tickets.jsonl"}),  # reading is fine
        ("Bash", {"command": "wc -l data/tickets/phase8_tickets.jsonl"}),
        ("Bash", {"command": "uv run pytest"}),
        ("Edit", {"file_path": "/repo/data/tickets/tickets.jsonl"}),  # the dev set is editable
    ],
)
def test_allowed(tool: str, tool_input: dict[str, str]) -> None:
    assert run_hook(tool, **tool_input) == 0
