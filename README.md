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

Then put the given OpenAI API key in `.env`.

## Commands

| Command | What it does |
|---|---|
| `uv run tka download` | Download the LangChain corpus and queries into `data/raw/` |
