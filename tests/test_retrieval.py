"""The search index must match the documents; an outdated index is refused, not silently used."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from helpdesk.retrieval import search as retrieval
from helpdesk.retrieval.embeddings import DIMENSIONS
from helpdesk.retrieval.knowledge_base import load_chunks
from helpdesk.storage.db import Connection, Database

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


def test_sync_copies_every_chunk_with_its_vector(db: Connection) -> None:
    assert retrieval.sync_index(db) == len(load_chunks())
    row = db.execute(
        "SELECT count(*) AS n, min(vector_dims(embedding)) AS dims FROM kb_chunks"
    ).fetchone()
    assert row == {"n": len(load_chunks()), "dims": DIMENSIONS}


def test_sync_again_changes_nothing_and_removes_deleted_chunks(db: Connection) -> None:
    retrieval.sync_index(db)
    before = db.execute("SELECT id, text, embedding::text FROM kb_chunks ORDER BY id").fetchall()
    db.execute(  # a chunk whose document section was deleted since the last sync
        "INSERT INTO kb_chunks SELECT 'gone.tr#1', doc, language, title, source, url, text,"
        " embedding FROM kb_chunks LIMIT 1"
    )
    retrieval.sync_index(db)
    after = db.execute("SELECT id, text, embedding::text FROM kb_chunks ORDER BY id").fetchall()
    assert after == before


def test_sql_search_matches_the_python_formula(db: Connection) -> None:
    # The old search: cosine similarity = dot product (vectors have length 1), best first.
    retrieval.sync_index(db)
    index = retrieval.load_index()
    query = index[5][1]  # a real chunk's vector as the "ticket"
    python = sorted(
        ((sum(x * y for x, y in zip(query, v, strict=True)), c.id) for c, v in index),
        reverse=True,
    )[:3]
    sql = retrieval.nearest(db, query, k=3)
    assert [chunk.id for _, chunk in sql] == [cid for _, cid in python]
    assert [score for score, _ in sql] == pytest.approx([s for s, _ in python], abs=1e-5)


def test_language_filter_returns_only_that_language(db: Connection) -> None:
    retrieval.sync_index(db)
    query = retrieval.load_index()[0][1]
    for language in ("tr", "en"):
        hits = retrieval.nearest(db, query, k=10, language=language)
        assert len(hits) == 10
        assert {chunk.language for _, chunk in hits} == {language}


def borrow_counter(db: Connection) -> tuple[Database, list[str]]:
    """A fake Database that records when a connection is borrowed and given back."""
    events: list[str] = []

    @contextmanager
    def database() -> Iterator[Connection]:
        events.append("borrow")
        yield db
        events.append("return")

    return database, events


def test_search_holds_no_connection_during_the_ai_call(
    db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    retrieval.sync_index(db)
    database, events = borrow_counter(db)
    vector = retrieval.load_index()[0][1]

    def fake_embed(texts: list[str]) -> list[list[float]]:
        events.append("embed")  # the slow AI call: no connection may be borrowed yet
        return [vector]

    monkeypatch.setattr(retrieval, "embed", fake_embed)
    hits = retrieval.search("ticket", database, language="tr")
    assert events == ["embed", "borrow", "return"]
    assert len(hits) == 3


def test_search_on_an_empty_knowledge_base_fails_loudly(
    db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, _ = borrow_counter(db)  # never synced: kb_chunks is empty
    monkeypatch.setattr(retrieval, "embed", lambda texts: [[0.0] * DIMENSIONS])
    with pytest.raises(RuntimeError, match="knowledge base is empty"):
        retrieval.search("ticket", database)


def test_every_chunk_has_an_official_link() -> None:
    assert all(chunk.url.startswith("https://") for chunk in load_chunks())


def test_every_section_exists_in_turkish_and_english() -> None:
    # Search runs in the ticket's language: a section missing in one language cannot answer there.
    ids = {chunk.id for chunk in load_chunks()}
    assert {i.replace(".tr#", ".en#") for i in ids if ".tr#" in i} == {
        i for i in ids if ".en#" in i
    }
