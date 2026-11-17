# Technical Knowledge Assistant

A command-line assistant that answers LangChain questions using only the FreshStack LangChain corpus (October 2024), and cites the corpus documents it used.

The assignment is in [Docs/assignment.md](Docs/assignment.md).

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/m-veck/Technical-Knowledge-Assistant
cd Technical-Knowledge-Assistant
uv sync
cp .env.example .env
```

Then put the given Anthropic and Cohere API keys in `.env`.

## Commands

| Command | What it does |
|---|---|
| `uv run tka download` | Download the LangChain corpus and queries into `data/raw/` |
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
