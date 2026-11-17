"""Search the index three ways: keyword (BM25), semantic (vectors) and hybrid (both, fused on their scores).

Every search function returns a list of (doc_id, score) pairs, best first.
"""

import re
import sqlite3

import sqlite_vec

from tka import config, database
from tka.embedding import embed_query

WORD = re.compile(r"\w+")  # letters, digits and underscores, so `langchain_core` stays one word


def keyword_query(question: str) -> str:
    """Turn a question into an FTS5 query: every distinct word in quotes, joined with OR."""
    words = dict.fromkeys(WORD.findall(question))  # dict keeps the order and drops repeats
    return " OR ".join(f'"{word}"' for word in words)


def search_keyword(conn: sqlite3.Connection, question: str, k: int) -> list[tuple[str, float]]:
    """BM25 over the document texts. FTS5's bm25() is lower-is-better, so the score is negated."""
    query = keyword_query(question)
    if not query:
        return []
    return conn.execute(
        "SELECT d.id, -bm25(documents_fts) FROM documents_fts JOIN documents d ON d.rowid = documents_fts.rowid "
        "WHERE documents_fts MATCH ? ORDER BY bm25(documents_fts) LIMIT ?",
        (query, k),
    ).fetchall()


def search_semantic(conn: sqlite3.Connection, question: str, k: int, vector: list[float] | None = None) -> list[tuple[str, float]]:
    """The k vectors closest to the question. The score is cosine similarity (1 - cosine distance).

    Embeds the question, unless the caller already has its vector (the evaluation keeps them in a file).
    """
    # Vector cache
    if vector is None:
        vector = embed_query(question)
    return conn.execute(
        "SELECT d.id, 1 - v.distance FROM documents_vec v JOIN documents d ON d.rowid = v.rowid "
        "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
        (sqlite_vec.serialize_float32(vector), k),
    ).fetchall()


def scaled(results: list[tuple[str, float]]) -> dict[str, float]:
    """The scores of one result list scaled to 0..1: its best document gets 1, its worst gets 0."""
    if not results:
        return {}
    values = [score for _doc_id, score in results]
    low, high = min(values), max(values)
    return {doc_id: (score - low) / (high - low) if high > low else 1.0 for doc_id, score in results}


def search_hybrid(conn: sqlite3.Connection, question: str, k: int, vector: list[float] | None = None) -> list[tuple[str, float]]:
    """Both searches, fused on their scores: WEIGHT_SEMANTIC x semantic score + the rest x keyword score.

    BM25 scores and cosine similarities are on different scales, so each list is first scaled to 0..1.
    A document that is in only one of the two lists gets 0 from the other.
    """
    keyword = scaled(search_keyword(conn, question, config.KEYWORD_CANDIDATES))
    semantic = scaled(search_semantic(conn, question, config.SEMANTIC_CANDIDATES, vector))  # vector: from the cache, if given
    weight = config.WEIGHT_SEMANTIC
    scores = {
        doc_id: weight * semantic.get(doc_id, 0.0) + (1 - weight) * keyword.get(doc_id, 0.0)
        for doc_id in sorted(keyword.keys() | semantic.keys())  # sorted, so equal scores always come out in the same order
    }
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:k]


def search(conn: sqlite3.Connection, question: str, mode: str = "hybrid", k: int = config.SEARCH_TOP_K, vector: list[float] | None = None):
    """Run one of the three searches by name. `vector` is the question's embedding, if the caller already has it."""
    if mode == "keyword":
        return search_keyword(conn, question, k)
    if mode == "semantic":
        return search_semantic(conn, question, k, vector)
    return search_hybrid(conn, question, k, vector)


def show_search(question: str, mode: str, k: int) -> None:
    """Print the top results for a question, with their GitHub URL (for `tka search`)."""
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka download database` first (or build it yourself with `uv run tka setup` and `uv run tka index`).")
    conn = database.connect()
    results = search(conn, question, mode, k)
    print(f"{mode} search, top {len(results)}:")
    for rank, (doc_id, score) in enumerate(results, start=1):
        url = conn.execute("SELECT url FROM documents WHERE id = ?", (doc_id,)).fetchone()[0]
        print(f"{rank:>3}. {score:.4f}  {doc_id}")
        print(f"            {url}")
    conn.close()
