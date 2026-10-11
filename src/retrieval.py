"""Find the knowledge-base chunks that best match a ticket, using embeddings.

Build the index once: uv run python src/retrieval.py
"""

import json
import time
from pathlib import Path

from google.genai import types

from knowledge_base import Chunk, load_chunks
from llm import get_client
from logs import get_logger

logger = get_logger(__name__)

EMBED_MODEL = "gemini-embedding-2"  # Google's recommended embedding model; multilingual (TR and EN)
DIMENSIONS = 768  # one of Google's recommended sizes; smaller than the 3072 default, still precise
BATCH_SIZE = 40  # texts per API call
BATCH_PAUSE = (
    60  # seconds between batches: the free tier allows 100 texts per minute, and each text counts
)


def query_text(ticket: str) -> str:
    """Google's recommended format for a search query with gemini-embedding-2."""
    return f"task: search result | query: {ticket}"


def document_text(title: str, text: str) -> str:
    """Google's recommended format for a document that will be searched."""
    return f"title: {title} | text: {text}"


def embed(texts: list[str]) -> list[list[float]]:
    """Return one vector per text. Each text is its own Content, so it gets its own vector."""
    config = types.EmbedContentConfig(output_dimensionality=DIMENSIONS)
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        if start > 0:
            time.sleep(BATCH_PAUSE)
        contents: list[types.ContentUnion] = [
            types.Content(parts=[types.Part.from_text(text=t)])
            for t in texts[start : start + BATCH_SIZE]
        ]
        started = time.perf_counter()
        result = get_client().models.embed_content(
            model=EMBED_MODEL, contents=contents, config=config
        )
        # No token count comes back for embeddings, so no cost estimate here (honest gap).
        ms = round((time.perf_counter() - started) * 1000)
        logger.info("embedding_call", model=EMBED_MODEL, texts=len(contents), ms=ms)
        embeddings = result.embeddings or []
        if len(embeddings) != len(contents):
            raise RuntimeError(
                f"Asked for {len(contents)} vectors, Gemini returned {len(embeddings)}."
            )
        for embedding in embeddings:
            if embedding.values is None:
                raise RuntimeError("Gemini returned an empty vector.")
            vectors.append(embedding.values)
    return vectors


Index = list[tuple[Chunk, list[float]]]  # every chunk with its vector

INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "kb_index.json"


def build_index() -> None:
    """Embed every chunk once and save the vectors, so searching later needs only one API call."""
    chunks = load_chunks()
    vectors = embed([document_text(c.title, c.text) for c in chunks])
    rows = [
        c.model_dump() | {"vector": [round(x, 6) for x in v]}
        for c, v in zip(chunks, vectors, strict=True)
    ]
    INDEX_PATH.write_text(
        json.dumps(
            {"model": EMBED_MODEL, "dimensions": DIMENSIONS, "chunks": rows}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(rows)} chunk vectors to {INDEX_PATH.name}")


def load_index() -> Index:
    """Every chunk with its saved vector. The documents are the source of truth for the chunks;
    the index file only adds the vectors, and must still match the documents."""
    saved = {row["id"]: row for row in json.loads(INDEX_PATH.read_text(encoding="utf-8"))["chunks"]}
    chunks = load_chunks()
    stale = [c.id for c in chunks if c.id not in saved or saved[c.id]["text"] != c.text]
    if stale or len(saved) != len(chunks):
        raise RuntimeError(
            f"The search index is out of date ({len(stale)} changed chunks, {len(saved)} saved "
            f"vs {len(chunks)} now). Rebuild it: uv run python src/retrieval.py"
        )
    return [(c, saved[c.id]["vector"]) for c in chunks]


def similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity. The vectors are already normalized (length 1), so it is just the dot product."""
    return sum(x * y for x, y in zip(a, b, strict=True))


def search(
    ticket: str, index: Index, k: int = 3, language: str | None = None
) -> list[tuple[float, Chunk]]:
    """The k chunks most similar to the ticket, best first.

    language ("tr"/"en"): only search chunks in that language, so the same rule does not appear twice (TR + EN).
    """
    query = embed([query_text(ticket)])[0]
    scored = [
        (similarity(query, vector), chunk)
        for chunk, vector in index
        if language is None or chunk.language == language
    ]
    return sorted(scored, key=lambda pair: pair[0], reverse=True)[:k]


if __name__ == "__main__":
    build_index()
