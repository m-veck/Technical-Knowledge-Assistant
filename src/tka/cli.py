"""The `tka` command. Each subcommand is a thin wrapper around a module in this package."""

from enum import Enum
from typing import Annotated

import typer

from tka import config
from tka.database import delete_database, setup_database
from tka.download import download_data
from tka.ingest import build_index
from tka.retrieval import show_search
from tka.split import make_split

app = typer.Typer(no_args_is_help=True)


class Mode(str, Enum):
    """The three ways to search, shown as choices in --help."""

    keyword = "keyword"
    semantic = "semantic"
    hybrid = "hybrid"


@app.callback()
def main() -> None:
    """Technical Knowledge Assistant: answers LangChain questions from the FreshStack corpus."""


@app.command()
def download() -> None:
    """Download the LangChain corpus and queries into data/raw/."""
    download_data()


@app.command()
def setup(
    clean: Annotated[bool, typer.Option("--clean", help="Delete the database first (asks for confirmation).")] = False,
) -> None:
    """Create the database and its tables in data/ (safe to rerun)."""
    if clean:
        answer = typer.prompt(f'This deletes {config.DB_PATH} and all its embeddings. Type "delete" to continue')
        if answer != "delete":
            typer.echo("Cancelled, nothing deleted.")
            raise typer.Exit()
        delete_database()
    setup_database()


@app.command()
def index(
    limit: Annotated[int | None, typer.Option(help="Only index this many new rows (for a test run).")] = None,
) -> None:
    """Embed corpus rows and store them in the database. Continues where the last run stopped."""
    build_index(limit)


@app.command()
def split() -> None:
    """Split the queries once into dev (tuning) and test (final run); writes splits/split.json."""
    make_split()


@app.command()
def search(
    question: str,
    mode: Annotated[Mode, typer.Option(help="keyword (BM25), semantic (vectors) or hybrid (both, fused).")] = Mode.hybrid,
    k: Annotated[int, typer.Option(help="How many results to show.")] = config.SEARCH_TOP_K,
) -> None:
    """Search the index and show the top results (no answer yet, just the retrieved documents)."""
    show_search(question, mode.value, k)
