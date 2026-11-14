"""Paths and settings for the whole project. Other modules import from here."""

from pathlib import Path

# Repo root: this file is src/tka/config.py, so two levels above the package folder
ROOT = Path(__file__).resolve().parents[2]

# Downloaded datasets (staging area, gitignored)
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CORPUS_DIR = RAW_DIR / "corpus"
QUERIES_DIR = RAW_DIR / "queries"  # evaluation only, never feeds the index

# Evaluation outputs
RESULTS_DIR = ROOT / "results"

# Hugging Face datasetes
CORPUS_DATASET = "freshstack/corpus-oct-2024"
QUERIES_DATASET = "freshstack/queries-oct-2024"
SUBSET = "langchain"
CORPUS_SPLIT = "train"
QUERIES_SPLIT = "test"
