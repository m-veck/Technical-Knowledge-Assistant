"""Download the LangChain subset of the FreshStack corpus and queries into data/raw/."""

from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from tka import config


def fetch(repo_id: str, filename: str, revision: str, target_dir: Path) -> Path:
    """Download one parquet file from a Hugging Face dataset repo, pinned to a fixed commit."""
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type="dataset",
        revision=revision,
        local_dir=target_dir,
    )
    return Path(path)


def check(name: str, path: Path, expected_rows: int) -> None:
    """Print the row count and file size, and flag a row count that differs from what we expect."""
    rows = pq.read_metadata(path).num_rows
    size_mb = path.stat().st_size / 1_000_000
    status = "OK" if rows == expected_rows else f"expected {expected_rows:,}"
    print(f"{name}: {rows:,} rows, {size_mb:.1f} MB ({status})")


def download_data() -> None:
    """Download the corpus and the queries, then check both."""
    corpus = fetch(config.CORPUS_DATASET, config.CORPUS_FILE, config.CORPUS_REVISION, config.CORPUS_DIR)
    queries = fetch(config.QUERIES_DATASET, config.QUERIES_FILE, config.QUERIES_REVISION, config.QUERIES_DIR)
    check("Corpus", corpus, config.CORPUS_ROWS)
    check("Queries", queries, config.QUERIES_ROWS)
