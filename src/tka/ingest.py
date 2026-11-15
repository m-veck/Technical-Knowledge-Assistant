"""Build the index: corpus rows -> units -> embeddings -> database. Rows already indexed are skipped."""

import re

import pyarrow.parquet as pq

from tka import config, database
from tka.embedding import embed_documents

BASE64_RUN = re.compile(rf"[A-Za-z0-9+/]{{{config.BASE64_MIN_LENGTH},}}={{0,2}}")


def read_corpus() -> list[dict]:
    """All corpus rows from the downloaded parquet file, with the metadata flattened."""
    table = pq.read_table(config.CORPUS_DIR / config.CORPUS_FILE)
    rows, seen = [], set()
    for row in table.to_pylist():
        if row["_id"] in seen:
            continue  # the corpus has 9 duplicate _ids with (near-)identical text: keep the first
        seen.add(row["_id"])
        rows.append(
            {
                "id": row["_id"],
                "text": row["text"],
                "url": row["metadata"]["url"],
                "start_byte": row["metadata"]["start_byte"],
                "end_byte": row["metadata"]["end_byte"],
            }
        )
    return rows


def clean_text(text: str) -> str:
    """Replace long base64 runs (image data) with a short placeholder."""
    return BASE64_RUN.sub(config.BASE64_PLACEHOLDER, text)


def make_units(rows: list[dict]) -> list[dict]:
    """Step 1: corpus rows become index units. Flat index: one unit per row. Chunking would split rows here.

    A row that was nothing but base64 is still stored, but marked as not searchable.
    """
    units = []
    for row in rows:
        text = clean_text(row["text"])
        units.append({**row, "text": text, "searchable": text.strip() != config.BASE64_PLACEHOLDER})
    return units


def build_index(limit: int | None = None) -> None:
    """Embed and store the rows that are not indexed yet; with a limit, only that many."""
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka setup` first.")
    conn = database.connect()
    done = database.indexed_ids(conn)
    rows = [row for row in read_corpus() if row["id"] not in done]
    if limit is not None:
        rows = rows[:limit]
    units = make_units(rows)
    searchable = [unit for unit in units if unit["searchable"]]
    not_searchable = [unit for unit in units if not unit["searchable"]]
    print(f"Already indexed: {len(done):,}. Indexing now: {len(units):,} ({len(not_searchable):,} only base64).")

    # Rows that were only base64: stored without a vector, so they stay out of both search indexes
    database.store_units(conn, not_searchable, [None] * len(not_searchable))

    billed_tokens = 0
    for start in range(0, len(searchable), config.EMBED_BATCH_SIZE):
        batch = searchable[start : start + config.EMBED_BATCH_SIZE]
        vectors, tokens = embed_documents([unit["text"] for unit in batch])  # step 2
        database.store_units(conn, batch, vectors)  # step 3
        billed_tokens += tokens
        print(f"  {start + len(batch):,} / {len(searchable):,} embedded and stored")
    conn.close()

    cost = billed_tokens / 1_000_000 * config.EMBED_PRICE_PER_MILLION
    print(f"Billed tokens: {billed_tokens:,} (about ${cost:.4f})")
    print(f"Database now holds {len(done) + len(units):,} of {config.CORPUS_ROWS:,} corpus rows.")
