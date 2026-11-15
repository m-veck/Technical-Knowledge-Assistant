"""Paths and settings for the whole project. Other modules import from here."""

from pathlib import Path

# Repo root: this file is src/tka/config.py, so two levels above the package folder
ROOT = Path(__file__).resolve().parents[2]

# Downloaded datasets (staging area, gitignored)
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CORPUS_DIR = RAW_DIR / "corpus"
QUERIES_DIR = RAW_DIR / "queries"  # evaluation only, never feeds the index

# SQLite database: corpus rows, BM25 index (FTS5) and vectors (sqlite-vec) in one file
DB_PATH = DATA_DIR / "tka.db"
EMBEDDING_DIM = 2048  # Cohere Embed v5 default

# Evaluation outputs
RESULTS_DIR = ROOT / "results"

# Hugging Face datasetes
CORPUS_DATASET = "freshstack/corpus-oct-2024"
QUERIES_DATASET = "freshstack/queries-oct-2024"
SUBSET = "langchain"
CORPUS_SPLIT = "train"
QUERIES_SPLIT = "test"

# Exact dataset commits (latest on 2026-11-15), so a later dataset update can't change our data
CORPUS_REVISION = "069f66dc323e163b48b10d08408d282733d4393b"
QUERIES_REVISION = "023ac3a14caf9d6ebb13d01adcfb8fa05e5a9630"

# Each subset and split is published as one parquet file
CORPUS_FILE = f"{SUBSET}/{CORPUS_SPLIT}-00000-of-00001.parquet"
QUERIES_FILE = f"{SUBSET}/{QUERIES_SPLIT}-00000-of-00001.parquet"

# Row counts for the check after download
CORPUS_ROWS = 49_514
QUERIES_ROWS = 203
