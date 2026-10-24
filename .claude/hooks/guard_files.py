"""PreToolUse hook: block any tool call that would touch the secrets file or change a locked test set.

Claude Code sends the planned tool call as JSON on stdin. Exit code 2 blocks the call and shows the
message on stderr to Claude, so it learns why. Exit code 0 lets the call run.
"""

import json
import re
import sys
from typing import NoReturn

LOCKED = ("data/tickets/test_tickets.jsonl", "data/tickets/phase8_tickets.jsonl")
# A path ending in ".env" (not ".env.example"): the file that holds the API key.
SECRETS = re.compile(r"(^|[\s/'\"=])\.env($|[\s'\";|&)])")
# Shell commands that write, move or delete files.
WRITES = re.compile(r">|\btee\b|\bsed\s+-i|\bmv\b|\brm\b|\bcp\b|\btruncate\b|\bdd\b|open\(.*['\"]w")


def block(reason: str) -> NoReturn:
    print(reason, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    call = json.load(sys.stdin)
    tool = call.get("tool_name", "")
    args = call.get("tool_input", {})
    if tool == "Bash":
        command = args.get("command", "")
        if SECRETS.search(command):
            block("Blocked: commands must never touch .env (it holds the API key). See CLAUDE.md.")
        if any(path in command for path in LOCKED) and WRITES.search(command):
            block("Blocked: the locked test sets are read-only. See ADR 0003.")
        return
    path = str(args.get("file_path") or args.get("notebook_path") or args.get("path") or "")
    if SECRETS.search(path):
        block("Blocked: .env holds the API key; never read or edit it. Use .env.example.")
    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"} and path.endswith(LOCKED):
        block("Blocked: the locked test sets are read-only (ADR 0003). Never edit or tune on them.")


if __name__ == "__main__":
    main()
