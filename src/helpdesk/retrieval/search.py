"""Find the knowledge-base chunks that best match a ticket, using embeddings.

Build the index once: uv run python -m helpdesk.retrieval.search
"""

import json

from psycopg_pool import ConnectionPool

from helpdesk.core.paths import DATA_DIR
from helpdesk.retrieval.embeddings import DIMENSIONS, EMBED_MODEL, document_text, embed, query_text
from helpdesk.retrieval.knowledge_base import Chunk, load_chunks
from helpdesk.storage.db import Connection, Database, open_pool

Index = list[tuple[Chunk, list[float]]]  # every chunk with its vector

INDEX_PATH = DATA_DIR / "kb_index.json"


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
            f"vs {len(chunks)} now). Rebuild it: uv run python -m helpdesk.retrieval.search"
        )
    return [(c, saved[c.id]["vector"]) for c in chunks]


def vector_literal(vector: list[float]) -> str:
    """pgvector's text form, e.g. "[0.1,0.2]"; Postgres turns it into a vector with ::vector."""
    return "[" + ",".join(str(x) for x in vector) + "]"


def sync_index(connection: Connection) -> int:
    """Copy the saved index into the kb_chunks table: add or update every chunk, remove chunks
    that no longer exist. One transaction, so a search never sees a half-updated table.
    No API calls: the vectors come from kb_index.json, so a fresh database (Neon) fills itself."""
    index = load_index()  # refuses an outdated index before anything is written
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO kb_chunks (id, doc, language, title, source, url, text, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)"
                " ON CONFLICT (id) DO UPDATE SET doc = excluded.doc, language = excluded.language,"
                " title = excluded.title, source = excluded.source, url = excluded.url,"
                " text = excluded.text, embedding = excluded.embedding",
                [
                    (c.id, c.doc, c.language, c.title, c.source, c.url, c.text, vector_literal(v))
                    for c, v in index
                ],
            )
        connection.execute("DELETE FROM kb_chunks WHERE id <> ALL(%s)", ([c.id for c, _ in index],))
    return len(index)


def open_synced_pool() -> ConnectionPool[Connection]:
    """The connection pool, with the knowledge base copied into the database once at startup."""
    pool = open_pool()
    with pool.connection() as connection:
        sync_index(connection)
    return pool


def nearest(
    connection: Connection, query: list[float], k: int = 3, language: str | None = None
) -> list[tuple[float, Chunk]]:
    """The k chunks closest in meaning to the query vector, best first.

    <=> is pgvector's cosine distance (0 = same meaning), so 1 - distance is the cosine similarity:
    the same score as before, so the decision's "strong match" threshold still applies.
    language ("tr"/"en"): only that language, so the same rule does not appear twice (TR + EN).
    """
    rows = connection.execute(
        "SELECT id, doc, language, title, source, url, text,"
        " 1 - (embedding <=> %(query)s::vector) AS score FROM kb_chunks"
        " WHERE %(language)s::text IS NULL OR language = %(language)s"
        " ORDER BY embedding <=> %(query)s::vector, id LIMIT %(k)s",
        {"query": vector_literal(query), "language": language, "k": k},
    ).fetchall()
    return [(row["score"], Chunk.model_validate(row)) for row in rows]


def search(
    ticket: str, database: Database, k: int = 3, language: str | None = None
) -> list[tuple[float, Chunk]]:
    """The k chunks most similar to the ticket, best first. The AI call comes first, so a
    database connection is borrowed only for the quick SQL query."""
    query = embed([query_text(ticket)])[0]
    with database() as connection:
        hits = nearest(connection, query, k, language)
    if not hits:  # the decision needs a best match; an empty table is a setup error, not "no match"
        raise RuntimeError("The knowledge base is empty in the database. Was sync_index run?")
    return hits


if __name__ == "__main__":
    build_index()
