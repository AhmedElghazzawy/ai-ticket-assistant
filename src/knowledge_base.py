"""Read the knowledge-base documents and split them into chunks (one chunk per "## " section)."""

from pathlib import Path

from pydantic import BaseModel

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


class Chunk(BaseModel):
    """One searchable piece of a document: a single rule with its heading."""

    id: str  # e.g. "sinavlar.tr#3": document name, language, section number
    doc: str  # e.g. "sinavlar": the same for the TR and EN versions
    language: str  # "tr" or "en"
    title: str  # the document title (first "# " line)
    source: str  # the official source line, so answers can cite it
    url: str  # the official link (the "- Bağlantı:" / "- Link:" line), so readers can check it
    text: str  # the section heading and its text

    @property
    def section(self) -> str:
        """The section heading, e.g. "Bütünleme sınavı (Madde 19)"."""
        return self.text.splitlines()[0].strip()


SOURCE_KEYS = ("- Kaynak:", "- Source:")
LINK_KEYS = ("- Bağlantı:", "- Link:")


def field_value(lines: list[str], keys: tuple[str, ...]) -> str | None:
    """The value of the first line starting with one of `keys`, e.g. "- Link: https://..."."""
    return next((line.split(":", 1)[1].strip() for line in lines if line.startswith(keys)), None)


def split_section(section: str, source: str, url: str) -> tuple[str, str, str]:
    """A section's text, source and link. Its own "- Kaynak:" / "- Bağlantı:" lines override the
    document's (for documents built from several sources) and are not part of the searchable text."""
    heading, *body = section.strip().splitlines()
    own = [line for line in body if line.startswith(SOURCE_KEYS + LINK_KEYS)]
    text = "\n".join([heading, *(line for line in body if line not in own)])
    return text, field_value(own, SOURCE_KEYS) or source, field_value(own, LINK_KEYS) or url


def split_document(path: Path) -> list[Chunk]:
    """Split one Markdown document into chunks at each '## ' heading."""
    doc, language = path.name.removesuffix(".md").split(".")  # "sinavlar.tr.md" -> "sinavlar", "tr"
    header, *sections = path.read_text(encoding="utf-8").split("\n## ")
    lines = header.splitlines()
    title = lines[0].removeprefix("# ").strip()
    source, url = field_value(lines, SOURCE_KEYS), field_value(lines, LINK_KEYS)
    if source is None or url is None:
        raise ValueError(f"{path.name}: the header needs a source line and a link line")
    chunks = []
    for n, section in enumerate(sections, start=1):
        text, section_source, section_url = split_section(section, source, url)
        chunks.append(
            Chunk(
                id=f"{doc}.{language}#{n}",
                doc=doc,
                language=language,
                title=title,
                source=section_source,
                url=section_url,
                text=text,
            )
        )
    return chunks


def load_chunks() -> list[Chunk]:
    """All chunks from all documents, in a fixed order."""
    return [chunk for path in sorted(KB_DIR.glob("*.md")) for chunk in split_document(path)]


if __name__ == "__main__":
    chunks = load_chunks()
    print(f"{len(chunks)} chunks from {len({c.doc for c in chunks})} topics")
    for language in ("tr", "en"):
        print(f"  {language}: {sum(c.language == language for c in chunks)} chunks")
    example = chunks[0]
    print(
        f"\nExample {example.id} | {example.title} | source: {example.source[:60]}...\n{example.text[:200]}..."
    )
