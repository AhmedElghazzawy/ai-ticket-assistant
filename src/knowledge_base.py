"""Read the knowledge-base documents and split them into chunks (one chunk per "## " section)."""

from pathlib import Path

from pydantic import BaseModel

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


class Chunk(BaseModel):
    """One searchable piece of a document: a single rule with its heading."""

    id: str        # e.g. "sinavlar.tr#3": document name, language, section number
    doc: str       # e.g. "sinavlar": the same for the TR and EN versions
    language: str  # "tr" or "en"
    title: str     # the document title (first "# " line)
    source: str    # the official source line, so answers can cite it
    text: str      # the section heading and its text


def split_document(path: Path) -> list[Chunk]:
    """Split one Markdown document into chunks at each '## ' heading."""
    doc, language = path.name.removesuffix(".md").split(".")  # "sinavlar.tr.md" -> "sinavlar", "tr"
    header, *sections = path.read_text(encoding="utf-8").split("\n## ")
    title = header.splitlines()[0].removeprefix("# ").strip()
    source = next(line for line in header.splitlines() if line.startswith(("- Kaynak:", "- Source:")))
    source = source.split(":", 1)[1].strip()
    return [
        Chunk(id=f"{doc}.{language}#{n}", doc=doc, language=language, title=title, source=source, text=section.strip())
        for n, section in enumerate(sections, start=1)
    ]


def load_chunks() -> list[Chunk]:
    """All chunks from all documents, in a fixed order."""
    return [chunk for path in sorted(KB_DIR.glob("*.md")) for chunk in split_document(path)]


if __name__ == "__main__":
    chunks = load_chunks()
    print(f"{len(chunks)} chunks from {len({c.doc for c in chunks})} topics")
    for language in ("tr", "en"):
        print(f"  {language}: {sum(c.language == language for c in chunks)} chunks")
    example = chunks[0]
    print(f"\nExample {example.id} | {example.title} | source: {example.source[:60]}...\n{example.text[:200]}...")
