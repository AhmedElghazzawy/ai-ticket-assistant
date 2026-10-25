"""Tests for splitting knowledge-base documents into chunks: tiny hand-made files, no AI calls."""

from pathlib import Path

from helpdesk.retrieval.knowledge_base import Chunk, split_document

DOCUMENT = """# Campus Life

- Source: Clubs Directive
- Link: https://example.edu/clubs.pdf

## Joining a club
Fill in the form.

## Dormitories (KYK)
- Source: Non-official source: dorm guide
- Link: https://example.com/dorms
Dorms belong to KYK.
"""


def chunks(tmp_path: Path) -> list[Chunk]:
    path = tmp_path / "kampus.en.md"
    path.write_text(DOCUMENT, encoding="utf-8")
    return split_document(path)


def test_section_without_its_own_source_uses_the_document_source(tmp_path: Path) -> None:
    club = chunks(tmp_path)[0]
    assert club.source == "Clubs Directive"
    assert club.url == "https://example.edu/clubs.pdf"


def test_section_source_overrides_the_document_source(tmp_path: Path) -> None:
    dorms = chunks(tmp_path)[1]
    assert dorms.source == "Non-official source: dorm guide"
    assert dorms.url == "https://example.com/dorms"


def test_source_lines_are_not_part_of_the_searchable_text(tmp_path: Path) -> None:
    # Keeps the text (and so the saved embedding) unchanged when a source is added.
    assert chunks(tmp_path)[1].text == "Dormitories (KYK)\nDorms belong to KYK."
