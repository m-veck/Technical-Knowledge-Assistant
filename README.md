# Technical Knowledge Assistant

![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white) ![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white) ![Claude Sonnet 5.5](https://img.shields.io/badge/LLM-Claude%20Sonnet%205.5-D97757?logo=anthropic&logoColor=white) ![Cohere Embed v5](https://img.shields.io/badge/embeddings-Cohere%20Embed%20v5-39594D) ![SQLite](https://img.shields.io/badge/index-SQLite%20%2B%20sqlite--vec-003B57?logo=sqlite&logoColor=white)

A command-line assistant that answers LangChain questions from the FreshStack LangChain corpus only, and cites the corpus documents behind every claim.

Built by Max van Eck as a technical case study. The assignment is in [Docs/assignment.md](Docs/assignment.md).

## How to start

You need Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Clone the repo and install the dependencies
git clone https://github.com/m-veck/Technical-Knowledge-Assistant
cd Technical-Knowledge-Assistant
uv sync

# 2. Put the .env file from the email in the repo root (see the note below)

# 3. Download the prebuilt database: the full index, about 700 MB
uv run tka download database

# 4. Ask a question
uv run tka ask "How do I add memory to a LangChain agent?"
```

> [!NOTE]
> The `.env` file holds the Anthropic and Cohere API keys. To use your own keys instead, copy `.env.example` to `.env` and fill them in.

> [!TIP]
> To run the evaluation as well, first fetch the FreshStack datasets with `uv run tka download datasets`. They hold the evaluation questions.

## Commands

| Command | What it does |
|---|---|
| `uv run tka download database` | Download the prebuilt database (the full index) from the GitHub Release into `data/tka.db` |
| `uv run tka download datasets` | Download the LangChain corpus and queries from Hugging Face into `data/raw/` (needed for the evaluation, or to build the index yourself) |
| `uv run tka setup` | Create the SQLite database and its tables in `data/` (safe to rerun; `--clean` deletes it first) |
| `uv run tka split` | Split the 203 evaluation questions once into dev (68) and test (135); writes `splits/split.json` (already done and committed) |
| `uv run tka search "question"` | Show the top retrieved documents for a question; `--mode keyword`, `semantic` or `hybrid` (default), `--k` for how many |
| `uv run tka index` | Embed the corpus rows and store them in the database; continues where the last run stopped (`--limit 100` for a test run) |
| `uv run tka evaluation retrieval` | Measure retrieval on the dev questions: Recall@50, Coverage@20 and alpha-nDCG@10 for keyword, semantic and hybrid search; writes `results/retrieval-dev-<date>-<time>.json`, one file per run (`--limit 5` for a test run, `--split test` for the final run). |

### The question cache

`splits/question_cache.json` holds the embedding of every evaluation question that has been run, one line per question.

- **Why:** tuning the search means rerunning the evaluation many times. With the cache, a rerun makes no embedding calls.
- **How it fills:** `tka evaluation retrieval` reads the file first and only embeds the questions that are missing.
- **Only the evaluation uses it.** `tka search` always embeds the question live, and nothing from the questions goes into the index.
- **If the embedding model changes:** the file records the model and dimension it was made with. If these differ from `src/tka/config.py`, the run stops and asks you to delete the file.
