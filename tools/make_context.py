"""Build claude_context.md: the whole project in one file, to paste into a Claude chat."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "claude_context.md"
FIRST = ["CLAUDE.md", "docs/ROADMAP.md", "docs/changelog.md"]  # shown first
RESTART = "facb85a"  # the "Start over from scratch" commit; history starts after it
RECENT = 3  # line-by-line changes only for the last commits; older ones as one-line titles (all on GitHub)
# Generated or machine-written files: listed with a note instead of their content.
SUMMARY_ONLY = (
    "eval/*.json",
    "data/kb_index.json",
    "uv.lock",
    "frontend/package-lock.json",
    "frontend/openapi.json",
    "frontend/src/client/*",
    "frontend/src/client/*/*",
)
# Git pathspecs left out of the history diffs: raw results (too big), and files already shown in full above.
NOT_IN_HISTORY = [
    *(f":(exclude){p}" for p in SUMMARY_ONLY),
    ":(exclude)docs/changelog.md",
    ":(exclude)data/knowledge_base",
]

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"}  # binary or not useful as text

INTRO = """# AI Ticket Assistant: full project context

I am a computer engineering student and a complete beginner in AI engineering.
Below is my whole project: the instructions (CLAUDE.md), the roadmap, the changelog (the story
of every change, every command and its result, and why), the full content of every
file, and at the end the git history: every commit title since the restart, and
every changed line of the most recent commits.
Please teach me: explain what each part does and why, in simple English,
with small examples. Ask me questions to check that I understood.
"""


def git(*args: str) -> str:
    """Run a git command in the project folder and return its output."""
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def project_files() -> list[Path]:
    """Return every file git can see (tracked or new), never ignored ones like .env."""
    files = [
        ROOT / line
        for line in git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    ]
    return [
        f
        for f in files
        if f.exists() and f.name != ".env" and f != OUTPUT and f.suffix not in IMAGES
    ]


def history_section() -> str:
    """All commit titles since the restart, the changed lines of the last RECENT commits,
    and uncommitted changes. (The full line-by-line history made the bundle too big to paste.)"""
    titles = git("log", "--reverse", "--format=- %h %ad %s", "--date=short", f"{RESTART}..HEAD")
    log = git(
        "log",
        "--reverse",
        "-p",
        f"-{RECENT}",
        "--diff-filter=M",  # changed files only: new files are shown in full above
        "--format=%n### Commit %h: %s (%ad)",
        "--date=short",
        "--",
        ".",
        *NOT_IN_HISTORY,
    )
    pending = git("diff", "HEAD", "--", ".", *NOT_IN_HISTORY)
    return (
        "\n---\n\n# History\n\n"
        f"## Every commit since the restart\n\n{titles.strip()}\n\n"
        f"## The last {RECENT} commits: changed lines of existing files\n\n"
        "Lines starting with + were added, lines starting with - were removed.\n\n"
        f"````diff\n{log.strip()}\n````\n\n"
        "## Changes not committed yet\n\n"
        f"````diff\n{pending.strip() or '(none)'}\n````\n"
    )


def file_section(path: Path) -> str:
    """Format one file as a heading followed by its full content."""
    name = path.relative_to(ROOT).as_posix()
    if any(path.match(pattern) for pattern in SUMMARY_ONLY):
        size = path.stat().st_size
        return f"\n---\n\n## File: {name}\n\n(Generated data, {size:,} bytes, not shown. Its numbers are in docs/changelog.md.)\n"
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
