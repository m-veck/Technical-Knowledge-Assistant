"""The evaluation questions: load the questions of a split, and keep their embeddings in a file.

Shared by the three evaluation runs (retrieval, answers, judge).
"""

import json

import pyarrow.parquet as pq

from tka import config
from tka.embedding import embed_query

# Eerst laden
def load_questions(split: str) -> list[dict]:
    """The questions of one split: the text to search with, and per nugget the set of relevant document ids."""
    query_ids = set(json.loads(config.SPLIT_PATH.read_text())[split])
    rows = pq.read_table(config.QUERIES_DIR / config.QUERIES_FILE).to_pylist()
    questions = []
    # Alle dev ophalen uit data set, en dan de nuggets erbij zetten.
    for row in rows:
        if row["query_id"] in query_ids:
            questions.append({
                "id": row["query_id"],
                "text": f"{row['query_title']} {row['query_text']}",  # title + body, as FreshStack does
                "nuggets": [set(nugget["relevant_corpus_ids"]) for nugget in row["nuggets"]],
            })
    return questions


def question_vectors(questions: list[dict]) -> dict[str, list[float]]:
    """The embedding of every question, by question id. Read from the cache file; only missing ones are embedded and added."""
    saved = {"model": config.QUERY_EMBED_MODEL, "dimension": config.EMBEDDING_DIM, "vectors": {}}
    if config.QUESTION_CACHE_PATH.exists():
        saved = json.loads(config.QUESTION_CACHE_PATH.read_text())
        if (saved["model"], saved["dimension"]) != (config.QUERY_EMBED_MODEL, config.EMBEDDING_DIM):
            raise SystemExit(
                f"{config.QUESTION_CACHE_PATH} was made with {saved['model']} at {saved['dimension']} dimensions, "
                "but config.py now says otherwise. Delete the file to embed the questions again."
            )

    missing = [question for question in questions if question["id"] not in saved["vectors"]]
    for question in missing:
        saved["vectors"][question["id"]] = embed_query(question["text"])
    if missing:
        # Written by hand instead of json.dumps, so every question's vector sits on its own line
        lines = [f'    "{question_id}": {json.dumps(vector)}' for question_id, vector in sorted(saved["vectors"].items())]
        config.QUESTION_CACHE_PATH.write_text(
            "{\n"
            f'  "model": "{saved["model"]}",\n'
            f'  "dimension": {saved["dimension"]},\n'
            '  "vectors": {\n' + ",\n".join(lines) + "\n  }\n}\n"
        )
    print(f"Question vectors: {len(questions) - len(missing)} from file, {len(missing)} newly embedded")
    return saved["vectors"]
