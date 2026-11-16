"""Split the queries once into a dev part (for tuning) and a test part (run once at the end)."""

import json
import random

import pyarrow.parquet as pq

from tka import config


def make_split() -> None:
    """Shuffle the query ids with a fixed seed and write the split to the repo. Refuses to overwrite it."""
    if config.SPLIT_PATH.exists():
        raise SystemExit(f"Split already exists: {config.SPLIT_PATH}. It is made once; delete the file by hand to redo it.")
    queries_file = config.QUERIES_DIR / config.QUERIES_FILE
    if not queries_file.exists():
        raise SystemExit("Queries not downloaded yet: run `uv run tka download` first.")

    # Only the ids are read: nothing else from the queries is needed or stored here
    query_ids = sorted(pq.read_table(queries_file, columns=["query_id"])["query_id"].to_pylist())
    random.Random(config.SPLIT_SEED).shuffle(query_ids)  # sorted first, so the result doesn't depend on file order

    split = {
        "dataset": config.QUERIES_DATASET,
        "revision": config.QUERIES_REVISION,
        "seed": config.SPLIT_SEED,
        "dev": sorted(query_ids[: config.SPLIT_DEV_SIZE]),
        "test": sorted(query_ids[config.SPLIT_DEV_SIZE :]),
    }
    config.SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.SPLIT_PATH.write_text(json.dumps(split, indent=2) + "\n")
    print(f"Split written to {config.SPLIT_PATH}: {len(split['dev'])} dev, {len(split['test'])} test (seed {config.SPLIT_SEED})")
