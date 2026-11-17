"""The `tka` command. Each subcommand is a thin wrapper around a module in this package."""

from enum import Enum
from typing import Annotated

import typer

from tka import config
from tka.ask import ask as ask_question
from tka.database import delete_database, setup_database
from tka.download import download_data
from tka.evaluation_retrieval import evaluate_retrieval
from tka.ingest import build_index
from tka.retrieval import show_search
from tka.split import make_split

app = typer.Typer(no_args_is_help=True)

# `tka evaluation` is a group: `tka evaluation retrieval`, and later `answers` and `judge`
evaluation_app = typer.Typer(no_args_is_help=True, help="Measure the quality of the retrieval and of the answers.")
app.add_typer(evaluation_app, name="evaluation")


class Split(str, Enum):
    """The two parts of the questions, shown as choices in --help."""

    dev = "dev"
    test = "test"


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
    """Search the index and show the top results (the retrieved documents only; `ask` gives an answer)."""
    show_search(question, mode.value, k)


@app.command()
def ask(
    question: Annotated[str | None, typer.Argument(help="The question. Leave it out to keep asking questions until `exit`.")] = None,
    model: Annotated[str, typer.Option(help="The Claude model that writes the answer.")] = config.LLM_MODEL,
    details: Annotated[bool, typer.Option("--details", help="Also show the statements behind the answer, each with its document ids.")] = False,
) -> None:
    """Answer a question from the corpus, with the documents each statement rests on.

    Every question is answered on its own: follow-up questions do not work.
    """
    ask_question(question, model, details)


@evaluation_app.command()
def retrieval(
    split: Annotated[Split, typer.Option(help="dev (for tuning) or test (the final run, once).")] = Split.dev,
    limit: Annotated[int | None, typer.Option(help="Only the first N questions (for a test run, nothing saved).")] = None,
) -> None:
    """Measure retrieval quality for keyword, semantic and hybrid search; saves to results/."""
    if split == Split.test:
        answer = typer.prompt('The test part is meant to be run once, at the end. Type "test" to continue')
        if answer != "test":
            typer.echo("Cancelled.")
            raise typer.Exit()
    evaluate_retrieval(split.value, limit)
