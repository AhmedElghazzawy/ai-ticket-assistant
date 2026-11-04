"""Tests for eval run metadata: every saved result must say what produced it. No AI calls."""

import subprocess
from pathlib import Path

import pytest

from helpdesk.ai import answer, classifier
from helpdesk.evals import report
from helpdesk.retrieval.search import INDEX_PATH


def test_text_hash_is_short_and_changes_with_the_text() -> None:
    first = report.text_hash("You are the ticket classifier.")
    assert len(first) == report.HASH_LENGTH
    assert first == report.text_hash("You are the ticket classifier.")
    assert first != report.text_hash("You are the ticket classifier!")


def test_both_prompts_are_fingerprinted() -> None:
    # A prompt change must show up in the result, even when the run was made before the commit.
    assert report.prompt_hashes() == {
        "classifier": report.text_hash(classifier.SYSTEM_PROMPT),
        "answer": report.text_hash(answer.SYSTEM_PROMPT),
    }


def test_run_metadata_records_code_prompts_data_and_model(tmp_path: Path) -> None:
    dataset = tmp_path / "tickets.jsonl"
    dataset.write_text('{"id": "x"}\n', encoding="utf-8")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    run = report.run_metadata("pipeline", "gemini-test", {"dev": dataset})

    assert run["suite"] == "pipeline"
    assert run["model"] == "gemini-test"
    assert run["git_commit"] == head
    assert isinstance(run["git_dirty"], bool)
    assert run["prompts"] == report.prompt_hashes()
    assert run["datasets"] == {"dev": report.file_hash(dataset)}
    assert run["kb_index"] == report.file_hash(INDEX_PATH)
    assert run["date"].endswith("+00:00")  # UTC, so runs from different machines sort correctly


def test_without_git_the_commit_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_git(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", no_git)
    assert report.git_state() == ("unknown", False)
