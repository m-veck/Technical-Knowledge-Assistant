"""Downloads: the FreshStack corpus and queries from Hugging Face, and the prebuilt database from GitHub."""

import shutil
import urllib.request
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


def download_datasets() -> None:
    """Download the corpus and the queries, then check both."""
    corpus = fetch(config.CORPUS_DATASET, config.CORPUS_FILE, config.CORPUS_REVISION, config.CORPUS_DIR)
    queries = fetch(config.QUERIES_DATASET, config.QUERIES_FILE, config.QUERIES_REVISION, config.QUERIES_DIR)
    check("Corpus", corpus, config.CORPUS_ROWS)
    check("Queries", queries, config.QUERIES_ROWS)


def download_database() -> None:
    """Download the prebuilt database from the GitHub Release into data/, so no one has to embed the corpus again."""
    if config.DB_PATH.exists():
        raise SystemExit(f"{config.DB_PATH} already exists. Delete it first (`uv run tka setup --clean`) to download it again.")
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Download to a .part file and rename at the end, so a broken-off download never looks like a finished database
    part = config.DB_PATH.with_suffix(".part")
    print("Downloading the database (about 700 MB), this can take a few minutes...")
    with urllib.request.urlopen(config.DB_RELEASE_URL) as response, open(part, "wb") as file:
        shutil.copyfileobj(response, file)
    part.rename(config.DB_PATH)
    print(f"Database ready: {config.DB_PATH} ({config.DB_PATH.stat().st_size / 1_000_000:.0f} MB)")
