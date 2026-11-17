"""Run the evaluation questions through the assistant and save every answer, with the numbers that need no judge.

Each question goes through answer(), the same function `tka ask` uses: hybrid search, then one Claude call.
The judge (evaluation_judge.py) later reads the saved file, so it can be rerun without paying for the answers again.
"""

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

import anthropic

from tka import config, database
from tka.answer import answer
from tka.evaluation_questions import load_questions, question_vectors


def current_settings() -> dict:
    """Everything that shapes an answer. Saved in the file, so a run can only be continued with the same settings."""
    return {
        "model": config.LLM_MODEL,
        "effort": config.LLM_EFFORT,
        "top_k": config.ANSWER_TOP_K,
        "weight_semantic": config.WEIGHT_SEMANTIC,
        "system_prompt": config.ANSWER_PROMPT_PATH.read_text(encoding="utf-8"),
    }


def summarise(answers: dict) -> dict:
    """The numbers that need no judge, over all answers so far."""
    entries = list(answers.values())
    nuggets = [found for entry in entries for found in entry["nuggets_retrieved"]]
    tokens_in = sum(entry["usage"]["input_tokens"] for entry in entries)
    tokens_out = sum(entry["usage"]["output_tokens"] for entry in entries)
    cost = (tokens_in * config.LLM_PRICE_INPUT_PER_MILLION + tokens_out * config.LLM_PRICE_OUTPUT_PER_MILLION) / 1_000_000
    return {
        "questions": len(entries),
        "outcomes": dict(Counter(entry["outcome"] for entry in entries)),
        "api_refusals": sum(entry["refusal"] is not None for entry in entries),
        "answers_with_invalid_citation": sum(bool(entry["invalid_citations"]) for entry in entries),
        "answers_with_violation": sum(bool(entry["violations"]) for entry in entries),
        "violations": dict(Counter(violation for entry in entries for violation in entry["violations"])),
        "nuggets": len(nuggets),
        "nuggets_retrieved": sum(nuggets),  # nuggets with a supporting document among the retrieved ones (official labels)
        # Not answered although a document for at least one nugget was retrieved: the candidates for a false refusal
        "not_answered_with_nuggets_retrieved": sum(entry["outcome"] != "answered" and any(entry["nuggets_retrieved"]) for entry in entries),
        "input_tokens": tokens_in,
        "output_tokens": tokens_out,
        "cost_usd": round(cost, 2),
        "cost_usd_per_question": round(cost / len(entries), 4),
        "seconds_per_question": round(sum(entry["seconds"] for entry in entries) / len(entries), 1),
    }


def evaluate_answers(split: str, limit: int | None = None, resume: Path | None = None) -> None:
    """Answer every question of the split and save the results. The file is written after every question.

    `resume` is the file of an earlier run: its questions are skipped and the new answers are added to it.
    """
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka download database` first (or build it yourself with `uv run tka setup` and `uv run tka index`).")

    # 1. A new results file, or the one of an earlier run to continue
    results = {"split": split, "settings": current_settings(), "summary": {}, "answers": {}}
    path = config.RESULTS_DIR / f"answers-{split}-{datetime.now():%Y-%m-%d-%H%M}.json"
    if resume:
        path = resume
        results = json.loads(path.read_text(encoding="utf-8"))
        if results["split"] != split or results["settings"] != current_settings():
            raise SystemExit(f"{path} was made for another split or with other settings (model, prompt, top-k), so it cannot be continued.")

    # 2. The questions still to do
    questions = load_questions(split)[:limit]
    vectors = question_vectors(questions)
    todo = [question for question in questions if question["id"] not in results["answers"]]
    print(f"{len(questions) - len(todo)} questions already in the file, {len(todo)} to answer")
    conn = database.connect()

    # 3. Answer them one by one
    for number, question in enumerate(todo, start=1):
        try:
            result = answer(conn, question["text"], vectors[question["id"]])
        except anthropic.APIError as error:  # rate limit, network, credit: stop here, the answers so far are saved
            print(f"\nAnthropic API error: {error.message}\nStopped. Continue with: uv run tka evaluation answers --split {split} --resume {path}")
            break
        # Per nugget: was a document that supports it among the retrieved ones? (from the official labels, no judge)
        retrieved_ids = {document["doc_id"] for document in result["retrieved"]}
        result["nuggets_retrieved"] = [bool(nugget & retrieved_ids) for nugget in question["nuggets"]]
        results["answers"][question["id"]] = result
        results["summary"] = summarise(results["answers"])

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"  {number}/{len(todo)} {result['outcome']:<16} nuggets retrieved {sum(result['nuggets_retrieved'])}/{len(question['nuggets'])}"
            f"  {result['seconds']:>5} s  {'; '.join(result['violations'])}"
        )
    conn.close()

    # 4. Print the summary
    if results["answers"]:
        print(f"\nAnswers on {split} ({len(results['answers'])} questions)")
        for name, value in results["summary"].items():
            print(f"  {name:<38} {value}")
        print(f"\nSaved to {path}")
