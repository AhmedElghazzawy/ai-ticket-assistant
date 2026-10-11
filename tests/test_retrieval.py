"""The search index must match the documents; an outdated index is refused, not silently used."""

import json
from pathlib import Path

import pytest

import retrieval
from knowledge_base import load_chunks

REAL_INDEX = retrieval.INDEX_PATH  # read before any test points INDEX_PATH elsewhere


def write_index(path: Path, change_text: bool) -> None:
    """A copy of the real index, optionally with one chunk's text changed (as if a document was edited)."""
    data = json.loads(REAL_INDEX.read_text(encoding="utf-8"))
    if change_text:
        data["chunks"][0]["text"] += " (edited)"
    path.write_text(json.dumps(data), encoding="utf-8")


def test_index_matching_the_documents_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retrieval, "INDEX_PATH", tmp_path / "index.json")
    write_index(retrieval.INDEX_PATH, change_text=False)
    assert len(retrieval.load_index()) == len(load_chunks())


def test_outdated_index_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retrieval, "INDEX_PATH", tmp_path / "index.json")
    write_index(retrieval.INDEX_PATH, change_text=True)
    with pytest.raises(RuntimeError, match="out of date"):
        retrieval.load_index()


def test_every_chunk_has_an_official_link() -> None:
    assert all(chunk.url.startswith("https://") for chunk in load_chunks())
