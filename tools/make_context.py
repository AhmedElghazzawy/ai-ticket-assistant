"""Build claude_context.md: the whole project in one file, to paste into a Claude chat."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "claude_context.md"
FIRST = ["CLAUDE.md", "docs/changelog.md"]  # shown before all other files
RESTART = "facb85a"  # the "Start over from scratch" commit; history starts after it
SUMMARY_ONLY = "eval/*.json"  # raw model predictions: too big to paste; their numbers are in the changelog
# Git pathspecs left out of the history diffs: raw results (too big) and the changelog (shown in full above).
NOT_IN_HISTORY = [f":(exclude){SUMMARY_ONLY}", ":(exclude)docs/changelog.md"]

INTRO = """# AI Ticket Assistant: full project context

I am a computer engineering student and a complete beginner in AI engineering.
Below is my whole project: the instructions (CLAUDE.md), the changelog (the story
of every change, every command and its result, and why), the full content of every
file, and at the end the git history with every changed line since the restart.
Please teach me: explain what each part does and why, in simple English,
with small examples. Ask me questions to check that I understood.
"""


def git(*args: str) -> str:
    """Run a git command in the project folder and return its output."""
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def project_files() -> list[Path]:
    """Return every file git can see (tracked or new), never ignored ones like .env."""
    files = [ROOT / line for line in git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()]
    return [f for f in files if f.exists() and f.name != ".env" and f != OUTPUT]


def history_section() -> str:
    """Every commit since the restart with its changed lines, plus uncommitted changes."""
    log = git("log", "--reverse", "-p", "--format=%n### Commit %h: %s (%ad)", "--date=short",
              f"{RESTART}..HEAD", "--", ".", *NOT_IN_HISTORY)
    pending = git("diff", "HEAD", "--", ".", *NOT_IN_HISTORY)
    return (
        "\n---\n\n# History: every change, line by line\n\n"
        "Lines starting with + were added, lines starting with - were removed.\n\n"
        f"````diff\n{log.strip()}\n````\n\n"
        "## Changes not committed yet\n\n"
        f"````diff\n{pending.strip() or '(none)'}\n````\n"
    )


def file_section(path: Path) -> str:
    """Format one file as a heading followed by its full content."""
    name = path.relative_to(ROOT).as_posix()
    if path.match(SUMMARY_ONLY):
        size = path.stat().st_size
        return f"\n---\n\n## File: {name}\n\n(Raw predictions, {size:,} bytes, not shown. The scores are in docs/changelog.md.)\n"
    language = path.suffix.lstrip(".") or "text"
    content = path.read_text(encoding="utf-8").rstrip()
    return f"\n---\n\n## File: {name}\n\n````{language}\n{content}\n````\n"


def main() -> None:
    files = project_files()
    first = [ROOT / name for name in FIRST]
    rest = sorted(f for f in files if f not in first)
    text = INTRO + "".join(file_section(f) for f in first + rest) + history_section()
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(first + rest)} files, {len(text):,} characters")


if __name__ == "__main__":
    main()
