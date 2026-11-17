"""Paths and settings for the whole project. Other modules import from here."""

from pathlib import Path

from dotenv import load_dotenv

# =======================================================
# General: repo root and API keys
# =======================================================

# Repo root: this file is src/tka/config.py, so two levels above the package folder
ROOT = Path(__file__).resolve().parents[2]

# API keys come from .env in the repo root (template: .env.example)
load_dotenv(ROOT / ".env")

# =======================================================
# Download: the Hugging Face datasets and where they land
# =======================================================

# Downloaded datasets (staging area, gitignored)
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CORPUS_DIR = RAW_DIR / "corpus"
QUERIES_DIR = RAW_DIR / "queries"  # evaluation only, never feeds the index

# Hugging Face datasets
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

# =======================================================
# Setup: the SQLite database
# =======================================================

# SQLite database: corpus rows, BM25 index (FTS5) and vectors (sqlite-vec) in one file
DB_PATH = DATA_DIR / "tka.db"

# The prebuilt database (the full index), attached to a GitHub Release; fetched by `tka download database`
DB_RELEASE_URL = "https://github.com/m-veck/Technical-Knowledge-Assistant/releases/download/index-2026-11-17/tka.db"

# =======================================================
# Index: cleaning the rows and embedding them
# =======================================================

# Base64 blobs (images in notebook outputs, .zlib files) are replaced before indexing
BASE64_MIN_LENGTH = 200
BASE64_PLACEHOLDER = "[base64 removed]"

# Embeddings: Cohere Embed v5 (Pro and Fast share one vector space)
EMBED_PROVIDER = "cohere"
EMBED_MODEL = "embed-v5.0-pro"
EMBEDDING_DIM = 2048  # Cohere Embed v5 default
EMBED_BATCH_SIZE = 96  # Cohere's maximum number of texts per call
EMBED_PRICE_PER_MILLION = 0.12  # USD per 1M input tokens, only for the cost line after indexing

# =======================================================
# Search: question model and the tunable settings (tune on dev only)
# =======================================================

QUERY_EMBED_MODEL = "embed-v5.0-pro"  # same model as the index
SEARCH_TOP_K = 10  # results after fusion

# Hybrid search: score fusion, tuned on the dev questions (2026-11-16)
SEMANTIC_CANDIDATES = 200  # results the semantic search delivers to the fusion
KEYWORD_CANDIDATES = 50  # results the keyword search delivers to the fusion
WEIGHT_SEMANTIC = 0.7  # share of the semantic score in the fused score; keyword gets the rest (0.3)

# =======================================================
# Answer: the Claude call that writes the answer from the retrieved rows
# =======================================================

LLM_MODEL = "claude-sonnet-5-5"  # answering and judging; `--model` overrides it
LLM_EFFORT = "medium"  # how deep Claude thinks before answering: low, medium or high
LLM_PRICE_INPUT_PER_MILLION = 2.0  # USD per 1M input tokens of LLM_MODEL, only for the cost lines of the evaluation
LLM_PRICE_OUTPUT_PER_MILLION = 10.0  # USD per 1M output tokens (thinking included)
ANSWER_TOP_K = 10  # how many retrieved rows go to Claude
ANSWER_MAX_TOKENS = 16_000  # ceiling for Claude's thinking plus answer in one call
ANSWER_PROMPT_PATH = Path(__file__).parent / "prompts" / "answer-system-prompt.md"  # the system prompt, as plain text

# =======================================================
# Split: dev and test part of the evaluation questions
# =======================================================

# Made once, committed so reviewers see what we tuned and tested on
SPLIT_PATH = ROOT / "splits" / "split.json"
SPLIT_SEED = 42
SPLIT_DEV_SIZE = 68  # 1/3 dev for tuning, the other 135 are the test part, run once at the end

# =======================================================
# Evaluation metrics and their names in the output JSON
# =======================================================

# Evaluation outputs
RESULTS_DIR = ROOT / "results"

# The embeddings of the questions, saved so a rerun of the evaluation does not embed them again
QUESTION_CACHE_PATH = ROOT / "splits" / "question_cache.json"

# Retrieval metrics. FreshStack (the makers of this dataset) score search with three numbers,
# each over a fixed number of top results. We use the same three, so our numbers can be laid next to their leaderboard.
EVAL_RECALL_K = 50  # Recall@50: share of the relevant documents found in the top 50 (also how many results are fetched)
EVAL_COVERAGE_K = 20  # Coverage@20: share of the nuggets with a supporting document in the top 20
EVAL_NDCG_K = 10  # alpha-nDCG@10: are the top 10 well ordered, with documents for different nuggets near the top
EVAL_ALPHA = 0.5  # in alpha-nDCG: a second document for an already covered nugget counts for half

# The judge (evaluation only): two Claude calls per answer, each with its own system prompt.
# Two separate calls, so one verdict cannot colour the other. Same model as the answers, for cost.
JUDGE_NUGGETS_PROMPT_PATH = Path(__file__).parent / "prompts" / "judge-nuggets-prompt.md"  # is the answer complete and helpful?
JUDGE_SUPPORT_PROMPT_PATH = Path(__file__).parent / "prompts" / "judge-support-prompt.md"  # do the cited documents back the answer?

# `tka report`: the HTML page it fills with the numbers of a split, and the folder the reports go to
REPORT_TEMPLATE_PATH = Path(__file__).parent / "templates" / "report.html"
REPORTS_DIR = ROOT / "reports"