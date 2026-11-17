"""Turn the saved evaluation runs of one split into one HTML report.

Reads the three kinds of files in results/ (retrieval, answers, judge) and writes reports/report-<split>.html.
No API calls and no database: every number comes from those files. The page itself is templates/report.html;
this module only collects the numbers and puts them into it.
"""

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from tka import config


def newest(pattern: str) -> Path | None:
    """The newest file in results/ that matches the pattern (the names end in date and time, so the last one is the newest)."""
    return max(config.RESULTS_DIR.glob(pattern), default=None)


def question_entry(query_id: str, answer: dict, judged: dict, retrieval: dict) -> dict:
    """Everything the report shows about one question."""
    cited_ids = {source["doc_id"] for source in answer["sources"]}
    verdicts = [nugget["verdict"] for nugget in judged["nuggets"]]
    return {
        "id": query_id,
        "question": answer["question"],
        # A reply that Anthropic's safety check stopped is saved as out_of_scope with a refusal; the report shows it as what it is
        "outcome": "declined_by_api" if answer["refusal"] is not None else answer["outcome"],
        "answer": answer["answer"],
        "violations": answer["violations"],
        "seconds": answer["seconds"],
        "helpful": judged["helpful"],
        "helpful_reason": judged["helpful_reason"],
        "nuggets": [
            {"text": nugget["text"], "found": nugget["retrieved"], "verdict": nugget["verdict"], "reason": nugget["reason"]}
            for nugget in judged["nuggets"]
        ],
        "nugget_score": verdicts.count("full") / len(verdicts),
        "statements": judged["statements"],
        "claims": judged["unsupported_claims"],
        # The judge only gets the documents whose ids the citations name. When none of the cited ids was retrieved
        # (the answer cited a number instead of an id), it had no document to check the statements against.
        "judge_had_no_documents": bool(answer["citations"]) and not answer["sources"],
        "retrieved": [
            {"rank": document["rank"], "doc_id": document["doc_id"], "url": document["url"], "cited": document["doc_id"] in cited_ids}
            for document in answer["retrieved"]
        ],
        "search": retrieval["per_question"].get(query_id, {}).get("hybrid", {}),
    }


def totals(questions: list[dict]) -> dict:
    """The numbers of the report, counted from the questions themselves (not taken from the summaries in the files)."""
    answered = [question for question in questions if question["outcome"] == "answered"]
    nuggets = [nugget for question in questions for nugget in question["nuggets"]]
    judged_nuggets = [nugget for question in answered for nugget in question["nuggets"]]
    statements = [statement for question in answered for statement in question["statements"]]
    points = {"full": 1, "partial": 0.5, "none": 0}
    return {
        "questions": len(questions),
        "outcomes": dict(Counter(question["outcome"] for question in questions)),
        "answers_with_violation": sum(bool(question["violations"]) for question in questions),
        "violations": dict(Counter(violation for question in questions for violation in question["violations"])),
        # The search, as the answer step saw it: for how many nuggets was a labelled document among the retrieved ones?
        "nuggets": len(nuggets),
        "nuggets_found": sum(nugget["found"] for nugget in nuggets),
        # The nugget score per question, averaged over all questions. A question without an answer scores 0.
        "nugget_score_strict": sum(question["nugget_score"] for question in questions) / len(questions),
        "nugget_score_lenient": sum(
            sum(points[nugget["verdict"]] for nugget in question["nuggets"]) / len(question["nuggets"]) for question in questions
        ) / len(questions),
        # The verdicts, for answered questions only; the nuggets of the other questions are counted apart
        "nuggets_not_answered": len(nuggets) - len(judged_nuggets),
        "verdicts": dict(Counter(nugget["verdict"] for nugget in judged_nuggets)),
        "verdicts_found": dict(Counter(nugget["verdict"] for nugget in judged_nuggets if nugget["found"])),
        "verdicts_not_found": dict(Counter(nugget["verdict"] for nugget in judged_nuggets if not nugget["found"])),
        "helpful": dict(Counter(question["helpful"] for question in answered)),
        "statements": len(statements),
        "statement_verdicts": dict(Counter(statement["verdict"] for statement in statements)),
        "claims": sum(len(question["claims"]) for question in answered),
        "answers_with_claim": sum(bool(question["claims"]) for question in answered),
        "answers_without_documents": sum(question["judge_had_no_documents"] for question in answered),
        "statements_without_documents": sum(len(question["statements"]) for question in answered if question["judge_had_no_documents"]),
    }


def build_report(split: str) -> None:
    """Write reports/report-<split>.html from the newest retrieval and judge run of the split, and the answers the judge read."""
    judge_path = newest(f"judge-{split}-*.json")
    retrieval_path = newest(f"retrieval-{split}-*.json")
    if not judge_path or not retrieval_path:
        raise SystemExit(
            f"The report needs a retrieval run and a judge run of the {split} split in {config.RESULTS_DIR}.\n"
            f"Run `uv run tka evaluation retrieval --split {split}`, `uv run tka evaluation answers --split {split}` "
            "and `uv run tka evaluation judge <answers file>` first."
        )
    judge = json.loads(judge_path.read_text(encoding="utf-8"))
    answers_path = config.RESULTS_DIR / judge["answers_file"]
    if not answers_path.exists():
        raise SystemExit(f"{judge_path.name} was made from {judge['answers_file']}, which is not in {config.RESULTS_DIR}.")
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))

    questions = [
        question_entry(query_id, answers["answers"][query_id], judged, retrieval)
        for query_id, judged in judge["judged"].items()
    ]
    cost_answers = answers["summary"]["cost_usd"]
    cost_judge = judge["summary"]["cost_usd"]
    report = {
        "split": split,
        "made": f"{datetime.now():%d %B %Y, %H:%M}",
        "files": {"retrieval": retrieval_path.name, "answers": answers_path.name, "judge": judge_path.name},
        "answers_in_file": len(answers["answers"]),  # more than the judged ones when the judge run is not finished
        "settings": {
            "model": answers["settings"]["model"],
            "effort": answers["settings"]["effort"],
            "top_k": answers["settings"]["top_k"],
            "judge_model": judge["settings"]["model"],
            **retrieval["settings"],
        },
        "retrieval": {"questions": retrieval["questions"], "averages": retrieval["averages"]},
        "totals": totals(questions),
        "cost": {
            "answers": cost_answers,
            "judge": cost_judge,
            "answers_per_question": answers["summary"]["cost_usd_per_question"],
            "seconds_per_question": answers["summary"]["seconds_per_question"],
        },
        "questions": questions,
    }

    # The template holds one placeholder. Every "<" in the data is written as \u003c, so no text in an answer can end or break the script tag
    data = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    page = config.REPORT_TEMPLATE_PATH.read_text(encoding="utf-8").replace("/*REPORT_DATA*/null", data)
    path = config.REPORTS_DIR / f"report-{split}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    print(f"Report on {split}: {len(questions)} questions, from {retrieval_path.name}, {answers_path.name} and {judge_path.name}")
    print(f"Saved to {path}")
