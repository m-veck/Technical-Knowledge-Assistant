"""The terminal side of `tka ask`: ask for questions, show a spinner and print each answer with its sources.

The answering itself is in answer.py; this file only decides how it looks on screen.
"""

import sqlite3
import sys

import anthropic
from rich.console import Console
from rich.markdown import Markdown

from tka import config, database
from tka.answer import answer

sys.stdout.reconfigure(encoding="utf-8")  # Windows: output sent to a file (tka ask ... > out.txt) would crash on special characters
console = Console()  # prints to the terminal with colours, Markdown and the spinner


def show_line(text: str = "", style: str | None = None) -> None:
    """Print one line as it is, in a colour or style. Square brackets and long ids are left alone."""
    console.print(text, style=style, markup=False, highlight=False, soft_wrap=True)


def show_answer(result: dict, details: bool = False) -> None:
    """Print one result of answer(): the answer, then the documents it marks, each with its id and GitHub url.

    With `details` also the statements behind the answer, as the evaluation gets them.
    """
    # A line across the screen and a label, so the answer stands apart from the question
    console.rule(style="cyan")
    show_line("TKA answer:", "bold")
    console.print(Markdown(result["answer"]))  # the answer is Markdown: code blocks get colours, `names` are highlighted
    if result["sources"]:
        show_line("\nSources:", "bold")
        for source in result["sources"]:
            show_line(f"[{source['rank']}] {source['doc_id']}", "cyan")
            show_line(f"    {source['url']}", "dim")
    if details and result["citations"]:
        show_line("\nStatements:", "bold")
        for citation in result["citations"]:
            show_line(f"- {citation['statement']}")
            for doc_id in citation["doc_ids"]:
                show_line(f"    {doc_id}", "cyan")
    if result["violations"]:
        show_line(f"\nChecks this answer did not pass: {', '.join(result['violations'])}", "red")
    usage = result["usage"]
    show_line(
        f"\n[{result['outcome']} | {result['model']}, {usage['input_tokens']:,} tokens in, {usage['output_tokens']:,} out, {result['seconds']} s]",
        "dim",
    )


def answer_and_show(conn: sqlite3.Connection, question: str, model: str, details: bool) -> None:
    """Answer one question with a spinner on screen, then print the result."""
    try:
        # A spinner while the search and the Claude call run, so the screen is not silent for ten seconds
        with console.status("Searching the corpus and writing the answer..."):
            result = answer(conn, question, model=model)
    except anthropic.APIError as error:  # wrong key, rate limit, unknown model: show Anthropic's own message
        show_line(f"Anthropic API error: {error.message}", "red")
        return
    show_answer(result, details)


def ask(question: str | None, model: str, details: bool = False) -> None:
    """Answer one question, or keep asking for questions until `exit` (for `tka ask`)."""
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka download database` first (or build it yourself with `uv run tka setup` and `uv run tka index`).")
    conn = database.connect()

    if question:
        answer_and_show(conn, question, model, details)
    else:
        show_line("Ask a question about LangChain. Type `exit` to stop.", "bold")
        show_line("Follow-up questions do not work: every question is answered on its own, without the earlier ones.")
        label = "Question"
        while True:
            # A line across the screen, the label, and the question is typed under it
            show_line()
            console.rule(style="cyan")
            show_line(f"{label}:", "bold")
            text = input("> ").strip()
            if text == "exit":
                break
            if text:
                answer_and_show(conn, text, model, details)
                label = "New question"
    conn.close()
