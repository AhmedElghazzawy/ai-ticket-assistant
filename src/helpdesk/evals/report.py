"""Run metadata: every saved eval result says which code, prompts, data and model produced it.

A score is only worth something if it can be traced back. The git commit alone is not enough: an eval
is usually run before the change is committed, so the prompts, datasets and knowledge-base index are
fingerprinted too.
"""

import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from helpdesk.ai import answer, classifier
from helpdesk.core.paths import ROOT
from helpdesk.retrieval.search import INDEX_PATH

HASH_LENGTH = 12  # enough to tell versions apart, short enough to read in a diff


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:HASH_LENGTH]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:HASH_LENGTH]


def prompt_hashes() -> dict[str, str]:
    return {
        "classifier": text_hash(classifier.SYSTEM_PROMPT),
        "answer": text_hash(answer.SYSTEM_PROMPT),
    }


def git_state() -> tuple[str, bool]:
    """The current commit and whether tracked files have uncommitted changes."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # no git (e.g. inside the Docker image)
        return "unknown", False
    return commit, bool(changes.strip())


def run_metadata(suite: str, model: str, datasets: dict[str, Path]) -> dict[str, Any]:
    commit, dirty = git_state()
    return {
        "suite": suite,
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        "git_dirty": dirty,
        "model": model,
        "prompts": prompt_hashes(),
        "datasets": {name: file_hash(path) for name, path in datasets.items()},
        "kb_index": file_hash(INDEX_PATH),
    }
