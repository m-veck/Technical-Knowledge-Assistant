"""Search the index three ways: keyword (BM25), semantic (vectors) and hybrid (both, fused with RRF).

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


def search_semantic(conn: sqlite3.Connection, question: str, k: int) -> list[tuple[str, float]]:
    """The k vectors closest to the question. The score is cosine similarity (1 - cosine distance)."""
    vector = sqlite_vec.serialize_float32(embed_query(question))
    return conn.execute(
        "SELECT d.id, 1 - v.distance FROM documents_vec v JOIN documents d ON d.rowid = v.rowid "
        "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
        (vector, k),
    ).fetchall()


def search_hybrid(conn: sqlite3.Connection, question: str, k: int) -> list[tuple[str, float]]:
    """Both searches, fused with reciprocal rank fusion: each list adds weight / (RRF_K + rank) to a document."""
    scores: dict[str, float] = {}
    for results, weight in (
        (search_keyword(conn, question, config.SEARCH_CANDIDATES), config.WEIGHT_KEYWORD),
        (search_semantic(conn, question, config.SEARCH_CANDIDATES), config.WEIGHT_SEMANTIC),
    ):
        for rank, (doc_id, _score) in enumerate(results, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (config.RRF_K + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:k]


SEARCHES = {"keyword": search_keyword, "semantic": search_semantic, "hybrid": search_hybrid}


def search(conn: sqlite3.Connection, question: str, mode: str = "hybrid", k: int = config.SEARCH_TOP_K):
    """Run one of the three searches by name."""
    return SEARCHES[mode](conn, question, k)


def show_search(question: str, mode: str, k: int) -> None:
    """Print the top results for a question, with their GitHub URL (for `tka search`)."""
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka setup` and `uv run tka index` first.")
    conn = database.connect()
    results = search(conn, question, mode, k)
    print(f"{mode} search, top {len(results)}:")
    for rank, (doc_id, score) in enumerate(results, start=1):
        url = conn.execute("SELECT url FROM documents WHERE id = ?", (doc_id,)).fetchone()[0]
        print(f"{rank:>3}. {score:.4f}  {doc_id}")
        print(f"            {url}")
    conn.close()
