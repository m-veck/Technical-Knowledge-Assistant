"""Answer a question from the index: one search, then one Claude call that answers from the retrieved documents.

This is the engine behind `tka ask` and the evaluation. It prints nothing: answer() returns one dict.
"""

import json
import os
import re
import sqlite3
import time

import anthropic

from tka import config
from tka.retrieval import search

# The shape of Claude's reply. The API enforces it, so the reply is always valid JSON with these three fields.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "doc_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["statement", "doc_ids"],
                "additionalProperties": False,
            },
        },
        "insufficient_context": {"type": "boolean"},
    },
    "required": ["answer", "citations", "insufficient_context"],
    "additionalProperties": False,
}

# The answer marks its sources as [3]: the number of a document. Code is skipped, because a [0] in code is an index.
MARKER = re.compile(r"\[(\d+)\]")
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)  # fenced code blocks and inline code


def marked_numbers(text: str) -> list[int]:
    """The document numbers an answer marks like [3], each once, lowest first."""
    return sorted({int(number) for number in MARKER.findall(CODE.sub("", text))})


def claude_client() -> anthropic.Anthropic:
    """An Anthropic client, with a clear message if the API key is not set up."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is missing: put it in .env (see .env.example).")
    return anthropic.Anthropic()


def build_message(question: str, documents: list[tuple[str, str]]) -> str:
    """The user message: the documents first, then the question (the layout from Anthropic's guide for long inputs).

    Every document gets a number, its id in <source> and its text in <document_content>.
    """
    parts = [
        f'<document index="{index}">\n<source>{doc_id}</source>\n<document_content>\n{text}\n</document_content>\n</document>'
        for index, (doc_id, text) in enumerate(documents, start=1)
    ]
    return "<documents>\n" + "\n".join(parts) + "\n</documents>\n\nQuestion: " + question


def answer(conn: sqlite3.Connection, question: str, vector: list[float] | None = None, model: str = config.LLM_MODEL) -> dict:
    """Answer one question. Returns everything about it: what was retrieved, what Claude said and what it cost.

    `vector` is the question's embedding, if the caller already has it (the evaluation keeps them in a file).
    """
    start = time.perf_counter()

    # 1. Search: the top documents, with their text (for Claude) and their GitHub url (for the reader)
    results = search(conn, question, "hybrid", config.ANSWER_TOP_K, vector)
    documents = []
    retrieved = []
    for rank, (doc_id, score) in enumerate(results, start=1):
        text, url = conn.execute("SELECT text, url FROM documents WHERE id = ?", (doc_id,)).fetchone()
        documents.append((doc_id, text))
        retrieved.append({"rank": rank, "doc_id": doc_id, "score": score, "url": url})

    # 2. One Claude call: the system prompt, the documents and the question in, JSON out
    response = claude_client().messages.create(
        model=model,
        max_tokens=config.ANSWER_MAX_TOKENS,
        system=config.ANSWER_PROMPT_PATH.read_text(encoding="utf-8"),
        messages=[{"role": "user", "content": build_message(question, documents)}],
        output_config={
            "effort": config.LLM_EFFORT,
            "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
        },
    )

    result = {
        "question": question,
        "model": model,
        "retrieved": retrieved,
        "answer": None,
        "sources": [],  # the retrieved documents the answer marks with [n]
        "citations": [],  # the statements behind the answer, each with its document ids (for the evaluation)
        "insufficient_context": None,
        "invalid_markers": [],
        "invalid_citations": [],
        "refusal": None,
        "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
    }

    # 3. Claude's safety checks can decline a request: then there is no JSON, only Anthropic's reason
    if response.stop_reason == "refusal":
        details = response.stop_details
        result["refusal"] = {"category": details.category, "explanation": details.explanation} if details else {}
    else:
        reply = json.loads(next(block.text for block in response.content if block.type == "text"))
        result["answer"] = reply["answer"]
        result["citations"] = reply["citations"]
        result["insufficient_context"] = reply["insufficient_context"]

        # 4. Marker check: every [n] in the answer must be the number of a retrieved document
        numbers = marked_numbers(reply["answer"])
        result["sources"] = [retrieved[number - 1] for number in numbers if 1 <= number <= len(retrieved)]
        result["invalid_markers"] = [number for number in numbers if not 1 <= number <= len(retrieved)]

        # 5. Citation check: every cited id must be one of the retrieved documents
        retrieved_ids = {doc_id for doc_id, _score in results}
        cited_ids = {doc_id for citation in reply["citations"] for doc_id in citation["doc_ids"]}
        result["invalid_citations"] = sorted(cited_ids - retrieved_ids)

    result["seconds"] = round(time.perf_counter() - start, 1)
    return result
