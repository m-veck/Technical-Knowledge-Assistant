"""The SQLite database: one file with the corpus rows, a BM25 index (FTS5) and the vectors (sqlite-vec)."""

import sqlite3

import sqlite_vec

from tka import config


def connect() -> sqlite3.Connection:
    """Open the database and load the sqlite-vec extension."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """Create the three tables if they don't exist yet. They are linked by rowid."""
    conn.executescript(f"""
        -- The corpus rows: what we cite
        CREATE TABLE IF NOT EXISTS documents (
            rowid      INTEGER PRIMARY KEY,  -- explicit, so a VACUUM can't renumber it
            id         TEXT NOT NULL UNIQUE, -- the corpus _id
            text       TEXT NOT NULL,
            url        TEXT,
            start_byte INTEGER,
            end_byte   INTEGER
        );

        -- BM25: full-text index over documents.text, without storing the text twice
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(text, content='documents');

        -- One vector per document, compared with cosine similarity
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_vec USING vec0(
            embedding float[{config.EMBEDDING_DIM}] distance_metric=cosine
        );
    """)


def indexed_ids(conn: sqlite3.Connection) -> set[str]:
    """The corpus _ids that are already in the database."""
    return {row[0] for row in conn.execute("SELECT id FROM documents")}


def store_units(conn: sqlite3.Connection, units: list[dict], vectors: list[list[float] | None]) -> None:
    """Write each unit to the three tables under one rowid, then commit (so a crash loses one batch at most).

    A unit whose vector is None only goes into documents: stored and citeable, but not searchable.
    """
    for unit, vector in zip(units, vectors):
        cursor = conn.execute(
            "INSERT INTO documents (id, text, url, start_byte, end_byte) VALUES (?, ?, ?, ?, ?)",
            (unit["id"], unit["text"], unit["url"], unit["start_byte"], unit["end_byte"]),
        )
        if vector is None:
            continue
        rowid = cursor.lastrowid
        conn.execute("INSERT INTO documents_fts (rowid, text) VALUES (?, ?)", (rowid, unit["text"]))
        conn.execute(
            "INSERT INTO documents_vec (rowid, embedding) VALUES (?, ?)",
            (rowid, sqlite_vec.serialize_float32(vector)),
        )
    conn.commit()


def delete_database() -> None:
    """Delete the database file, including all stored embeddings."""
    config.DB_PATH.unlink(missing_ok=True)


def setup_database() -> None:
    """Create the database file and its tables, then report how many documents it holds."""
    conn = connect()
    create_tables(conn)
    count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    conn.close()
    print(f"Database ready: {config.DB_PATH} ({count:,} documents)")
