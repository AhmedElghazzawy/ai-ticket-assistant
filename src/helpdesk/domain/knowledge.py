"""A piece of an official document, as the search finds it and the answer cites it. Plain data:
the AI step, the search and the storage all use it, so it lives below all of them."""

from pydantic import BaseModel


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
