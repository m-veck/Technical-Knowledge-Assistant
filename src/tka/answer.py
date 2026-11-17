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

# What a question can lead to. Claude picks one; "answered" is the only one with citations.
OUTCOMES = ["answered", "not_in_corpus", "out_of_scope", "about_assistant"]

# The shape of Claude's reply. The API enforces it, so the reply is always valid JSON with these three fields.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": OUTCOMES},
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
    },
    "required": ["outcome", "answer", "citations"],
    "additionalProperties": False,
}

# The two answers that code gives itself, without Claude
NO_QUESTION = "That is not a question I can search for. Ask something about LangChain or one of the libraries around it."
DECLINED = "Claude's safety checks declined this question, so there is no answer. Try asking it in another way."

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


def retrieve_documents(conn: sqlite3.Connection, question: str, vector: list[float] | None = None) -> list[dict]:
    """The top documents for a question, each with its rank, id, score, GitHub url and text."""
    documents = []
    results = search(conn, question, "hybrid", config.ANSWER_TOP_K, vector)
    for rank, (doc_id, score) in enumerate(results, start=1):
        text, url = conn.execute("SELECT text, url FROM documents WHERE id = ?", (doc_id,)).fetchone()
        documents.append({"rank": rank, "doc_id": doc_id, "score": score, "url": url, "text": text})
    return documents


def build_message(question: str, documents: list[dict]) -> str:
    """The user message: the documents first, then the question (the layout from Anthropic's guide for long inputs).

    Every document gets its rank as number, its id in <source> and its text in <document_content>.
    The question has its own tag, so the prompt can say that everything inside the tags is data, not instructions.
    """
    parts = [
        f'<document index="{document["rank"]}">\n<source>{document["doc_id"]}</source>\n'
        f"<document_content>\n{document['text']}\n</document_content>\n</document>"
        for document in documents
    ]
    return "<documents>\n" + "\n".join(parts) + f"\n</documents>\n\n<question>\n{question}\n</question>"


def new_result(question: str, model: str, documents: list[dict], answer_text: str) -> dict:
    """The dict that answer() returns, filled in for a question that gets no answer from Claude."""
    return {
        "question": question,
        "model": model,
        "retrieved": [{key: value for key, value in document.items() if key != "text"} for document in documents],
        "outcome": "out_of_scope",
        "answer": answer_text,
        "citations": [],  # the statements behind the answer, each with its document ids
        "sources": [],  # the retrieved documents that the citations name
        "invalid_citations": [],  # cited ids that were not retrieved
        "violations": [],  # the rules of check_answer() that this answer breaks
        "refusal": None,  # Anthropic's reason, when its safety checks declined the question
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def check_answer(result: dict) -> list[str]:
    """The rules every answer must keep, whatever the question was. Returns the ones this answer breaks."""
    retrieved_ids = [document["doc_id"] for document in result["retrieved"]]
    cited_ids = {doc_id for citation in result["citations"] for doc_id in citation["doc_ids"]}
    numbers = marked_numbers(result["answer"])
    marked_ids = {retrieved_ids[number - 1] for number in numbers if 1 <= number <= len(retrieved_ids)}

    violations = []
    if result["invalid_citations"]:
        violations.append("cited id was not retrieved")
    if len(marked_ids) < len(numbers):
        violations.append("marker is not a retrieved document")
    if result["outcome"] == "answered":
        if not result["citations"]:
            violations.append("answered without a citation")
        if not numbers:
            violations.append("answered without a marker")
        if marked_ids != cited_ids & set(retrieved_ids):
            violations.append("marked and cited documents differ")
    else:
        if result["citations"]:
            violations.append("citations on an outcome that is not answered")
        if numbers:
            violations.append("markers on an outcome that is not answered")
    return violations


def answer_from_documents(question: str, documents: list[dict], model: str = config.LLM_MODEL) -> dict:
    """One Claude call: the system prompt, the documents and the question in, the checked answer out."""
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
    result = new_result(question, model, documents, DECLINED)
    result["usage"] = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}

    # Claude's safety checks can decline a request: then there is no JSON, only Anthropic's reason
    if response.stop_reason == "refusal":
        details = response.stop_details
        result["refusal"] = {"category": details.category, "explanation": details.explanation} if details else {}
        return result

    # The reply has the three fields of ANSWER_SCHEMA: outcome, answer and citations
    result.update(json.loads(next(block.text for block in response.content if block.type == "text")))

    # The sources come from the ids in the citations (enforced fields), not from the [n] markers in the text
    cited_ids = {doc_id for citation in result["citations"] for doc_id in citation["doc_ids"]}
    result["sources"] = [document for document in result["retrieved"] if document["doc_id"] in cited_ids]
    result["invalid_citations"] = sorted(cited_ids - {document["doc_id"] for document in result["retrieved"]})
    result["violations"] = check_answer(result)
    return result


def answer(conn: sqlite3.Connection, question: str, vector: list[float] | None = None, model: str = config.LLM_MODEL) -> dict:
    """Answer one question. Returns everything about it: what was retrieved, what Claude said and what it cost.

    `vector` is the question's embedding, if the caller already has it (the evaluation keeps them in a file).
    """
    start = time.perf_counter()
    if not re.search(r"\w", question):
        # No letter or digit: nothing to search for, so no paid calls
        result = new_result(question, model, [], NO_QUESTION)
    else:
        documents = retrieve_documents(conn, question, vector)
        result = answer_from_documents(question, documents, model)
    result["seconds"] = round(time.perf_counter() - start, 1)
    return result
