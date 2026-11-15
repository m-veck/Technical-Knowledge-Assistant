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
| `uv run tka index` | Embed the corpus rows and store them in the database; continues where the last run stopped (`--limit 100` for a test run) |
