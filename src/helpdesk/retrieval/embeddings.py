"""Turn text into vectors with gemini-embedding-2: similar meaning, nearby vectors."""

import time

from google.genai import types

from helpdesk.ai.gemini import get_client
from helpdesk.core.logs import get_logger

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
