"""The `tka` command. Each subcommand is a thin wrapper around a module in this package."""

import typer

from tka.download import download_data

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Technical Knowledge Assistant: answers LangChain questions from the FreshStack corpus."""


@app.command()
def download() -> None:
    """Download the LangChain corpus and queries into data/raw/."""
    download_data()
