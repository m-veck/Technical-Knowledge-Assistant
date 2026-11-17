"""Judge the saved answers of an answer run: are they complete, helpful and true to their sources?

Reads a file written by `tka evaluation answers`, so judging never pays for the answers again.
Per answer two Claude calls, each with its own system prompt:
  1. nuggets: does the answer say each nugget, and would it help the person who asked?
  2. support: do the cited documents back each statement, and does the answer claim anything without a source?
Code then combines call 1 with what the answer run already knows (was a document for the nugget retrieved?).
"""

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import time

import anthropic

from tka import config, database
from tka.answer import claude_client
from tka.evaluation_questions import load_questions

# The shape of the judge's reply to call 1 (nuggets). The API enforces it.
NUGGETS_SCHEMA = {
    "type": "object",
    "properties": {
        "nuggets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["full", "partial", "none"]},
                    "reason": {"type": "string"},
                },
                "required": ["number", "verdict", "reason"],
                "additionalProperties": False,
            },
        },
        "helpful": {"type": "string", "enum": ["yes", "partly", "no"]},
        "helpful_reason": {"type": "string"},
    },
    "required": ["nuggets", "helpful", "helpful_reason"],
    "additionalProperties": False,
}

# The shape of the judge's reply to call 2 (support)
SUPPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["supported", "partly", "not_supported"]},
                    "reason": {"type": "string"},
                },
                "required": ["number", "verdict", "reason"],
                "additionalProperties": False,
            },
        },
        "unsupported_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"quote": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["quote", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["statements", "unsupported_claims"],
    "additionalProperties": False,
}


def current_settings() -> dict:
    """Everything that shapes a verdict. Saved in the file, so a run can only be continued with the same settings."""
    return {
        "model": config.LLM_MODEL,
        "effort": config.LLM_EFFORT,
        "nuggets_prompt": config.JUDGE_NUGGETS_PROMPT_PATH.read_text(encoding="utf-8"),
        "support_prompt": config.JUDGE_SUPPORT_PROMPT_PATH.read_text(encoding="utf-8"),
    }


def nuggets_message(answer: dict, question: dict) -> str:
    """The user message of call 1: the question, the answer, the numbered nuggets and the reference answer. No documents."""
    nuggets = "\n".join(f"{number}. {text}" for number, text in enumerate(question["nugget_texts"], start=1))
    return (
        f"<question>\n{answer['question']}\n</question>\n\n"
        f"<answer>\n{answer['answer']}\n</answer>\n\n"
        f"<nuggets>\n{nuggets}\n</nuggets>\n\n"
        f"<reference_answer>\n{question['reference_answer']}\n</reference_answer>"
    )


def support_message(conn: sqlite3.Connection, answer: dict) -> str:
    """The user message of call 2: the cited documents with their full text, then the statements, the answer and the question.

    Only the documents the answer cites are included, each with the number it has in the answer's [n] markers.
    The question is there so the judge can tell what the answer says about the user's own code or error.
    """
    documents = []
    for source in answer["sources"]:
        (text,) = conn.execute("SELECT text FROM documents WHERE id = ?", (source["doc_id"],)).fetchone()
        documents.append(
            f'<document index="{source["rank"]}">\n<source>{source["doc_id"]}</source>\n'
            f"<document_content>\n{text}\n</document_content>\n</document>"
        )
    statements = "\n".join(
        f"{number}. {citation['statement']}\n   cites: {', '.join(citation['doc_ids'])}"
        for number, citation in enumerate(answer["citations"], start=1)
    )
    return (
        "<documents>\n" + "\n".join(documents) + "\n</documents>\n\n"
        f"<statements>\n{statements}\n</statements>\n\n"
        f"<answer>\n{answer['answer']}\n</answer>\n\n"
        f"<question>\n{answer['question']}\n</question>"
    )


def judge_call(prompt_path: Path, message: str, schema: dict, usage: dict) -> dict:
    """One Claude call of the judge. Returns the reply in the shape of `schema` and adds the tokens to `usage`."""
    response = claude_client().messages.create(
        model=config.LLM_MODEL,
        max_tokens=config.ANSWER_MAX_TOKENS,
        system=prompt_path.read_text(encoding="utf-8"),
        messages=[{"role": "user", "content": message}],
        output_config={"effort": config.LLM_EFFORT, "format": {"type": "json_schema", "schema": schema}},
    )
    usage["input_tokens"] += response.usage.input_tokens
    usage["output_tokens"] += response.usage.output_tokens
    return json.loads(next(block.text for block in response.content if block.type == "text"))


def bucket(retrieved: bool, verdict: str) -> str:
    """Where a nugget ended up: found by the search or not, said by the answer (verdict `full`) or not."""
    if retrieved:
        return "retrieved_and_used" if verdict == "full" else "retrieved_not_used"
    return "in_answer_without_labelled_document" if verdict == "full" else "not_retrieved"


def judge_answer(conn: sqlite3.Connection, answer: dict, question: dict) -> dict:
    """Judge one saved answer. An answer that is not `answered` gets no calls: its nuggets count as `none`."""
    start = time.perf_counter()
    usage = {"input_tokens": 0, "output_tokens": 0}
    nugget_verdicts = [{"verdict": "none", "reason": "The question was not answered."} for _ in question["nugget_texts"]]
    judged = {"outcome": answer["outcome"], "helpful": None, "helpful_reason": None, "statements": [], "unsupported_claims": []}

    if answer["outcome"] == "answered":
        # Call 1: the nuggets and the overall verdict
        reply = judge_call(config.JUDGE_NUGGETS_PROMPT_PATH, nuggets_message(answer, question), NUGGETS_SCHEMA, usage)
        nugget_verdicts = reply["nuggets"]
        judged["helpful"], judged["helpful_reason"] = reply["helpful"], reply["helpful_reason"]

        # Call 2: the statements against their cited documents, and the claims without a source
        reply = judge_call(config.JUDGE_SUPPORT_PROMPT_PATH, support_message(conn, answer), SUPPORT_SCHEMA, usage)
        judged["statements"] = [
            {"statement": citation["statement"], "doc_ids": citation["doc_ids"], "verdict": verdict["verdict"], "reason": verdict["reason"]}
            for citation, verdict in zip(answer["citations"], reply["statements"])
        ]
        judged["unsupported_claims"] = reply["unsupported_claims"]

    # Per nugget: the judge's verdict next to what the answer run knows from the official labels
    judged["nuggets"] = [
        {"text": text, "retrieved": retrieved, "verdict": verdict["verdict"], "reason": verdict["reason"], "bucket": bucket(retrieved, verdict["verdict"])}
        for text, retrieved, verdict in zip(question["nugget_texts"], answer["nuggets_retrieved"], nugget_verdicts)
    ]
    judged["usage"] = usage
    judged["seconds"] = round(time.perf_counter() - start, 1)
    return judged


def summarise(judged: dict) -> dict:
    """The totals over all judged answers so far."""
    entries = list(judged.values())
    nuggets = [nugget for entry in entries for nugget in entry["nuggets"]]
    statements = [statement for entry in entries for statement in entry["statements"]]
    tokens_in = sum(entry["usage"]["input_tokens"] for entry in entries)
    tokens_out = sum(entry["usage"]["output_tokens"] for entry in entries)
    cost = (tokens_in * config.LLM_PRICE_INPUT_PER_MILLION + tokens_out * config.LLM_PRICE_OUTPUT_PER_MILLION) / 1_000_000
    return {
        "questions": len(entries),
        "answered": sum(entry["outcome"] == "answered" for entry in entries),
        "helpful": dict(Counter(entry["helpful"] for entry in entries if entry["helpful"])),
        "nuggets": len(nuggets),
        "nugget_verdicts": dict(Counter(nugget["verdict"] for nugget in nuggets)),
        "nugget_buckets": dict(Counter(nugget["bucket"] for nugget in nuggets)),
        "statements": len(statements),
        "statement_verdicts": dict(Counter(statement["verdict"] for statement in statements)),
        "unsupported_claims": sum(len(entry["unsupported_claims"]) for entry in entries),
        "answers_with_unsupported_claim": sum(bool(entry["unsupported_claims"]) for entry in entries),
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "cost_usd": round(cost, 2),
        "cost_usd_per_question": round(cost / len(entries), 4),
    }


def evaluate_judge(answers_path: Path, limit: int | None = None, resume: Path | None = None) -> None:
    """Judge every answer in a file of `tka evaluation answers` and save the verdicts. The file is written after every question.

    `resume` is the file of an earlier judge run: its questions are skipped and the new verdicts are added to it.
    """
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    split = answers["split"]

    # 1. A new results file, or the one of an earlier run to continue
    results = {"answers_file": answers_path.name, "split": split, "settings": current_settings(), "summary": {}, "judged": {}}
    path = config.RESULTS_DIR / f"judge-{split}-{datetime.now():%Y-%m-%d-%H%M}.json"
    if resume:
        path = resume
        results = json.loads(path.read_text(encoding="utf-8"))
        if results["answers_file"] != answers_path.name or results["settings"] != current_settings():
            raise SystemExit(f"{path} was made for another answers file or with other settings (model, prompts), so it cannot be continued.")

    # 2. The answers still to judge. The nuggets and reference answers come from the questions file, by question id.
    questions = {question["id"]: question for question in load_questions(split)}
    todo = [query_id for query_id in list(answers["answers"])[:limit] if query_id not in results["judged"]]
    print(f"{len(results['judged'])} answers already judged, {len(todo)} to judge")
    conn = database.connect()

    # 3. Judge them one by one
    for number, query_id in enumerate(todo, start=1):
        try:
            judged = judge_answer(conn, answers["answers"][query_id], questions[query_id])
        except anthropic.APIError as error:  # rate limit, network, credit: stop here, the verdicts so far are saved
            print(f"\nAnthropic API error: {error.message}\nStopped. Continue with: uv run tka evaluation judge {answers_path} --resume {path}")
            break
        results["judged"][query_id] = judged
        results["summary"] = summarise(results["judged"])
        path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        full = sum(nugget["verdict"] == "full" for nugget in judged["nuggets"])
        supported = sum(statement["verdict"] == "supported" for statement in judged["statements"])
        print(
            f"  {number}/{len(todo)} nuggets in answer {full}/{len(judged['nuggets'])}  helpful {judged['helpful'] or '-':<6}"
            f"  statements supported {supported}/{len(judged['statements'])}  claims without source {len(judged['unsupported_claims'])}"
            f"  {judged['seconds']:>5} s"
        )
    conn.close()

    # 4. Print the summary
    if results["judged"]:
        print(f"\nJudge on {answers_path.name} ({len(results['judged'])} answers)")
        for name, value in results["summary"].items():
            print(f"  {name:<32} {value}")
        print(f"\nSaved to {path}")
