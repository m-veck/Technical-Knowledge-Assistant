"""Measure retrieval quality: Recall@50, Coverage@20 and alpha-nDCG@10 for keyword, semantic and hybrid search.

Each question has nuggets: the key facts of a good answer, each with the corpus rows that support it.
The three metrics follow the FreshStack definitions (the ones behind its leaderboard).
Each is computed per question and then averaged.
"""
from datetime import datetime
import json
import math

from tka import config, database
from tka.evaluation_questions import load_questions, question_vectors
from tka.retrieval import search # Comes out of retrieval.py

MODES = ["keyword", "semantic", "hybrid"]
METRICS = [f"Recall@{config.EVAL_RECALL_K}", f"Coverage@{config.EVAL_COVERAGE_K}", f"alpha-nDCG@{config.EVAL_NDCG_K}"]


def recall(ranked: list[str], nuggets: list[set[str]], k: int) -> float:
    """Share of all relevant documents (of any nugget) that is in the top k."""
    relevant = set().union(*nuggets)
    return len(relevant & set(ranked[:k])) / len(relevant)


def coverage(ranked: list[str], nuggets: list[set[str]], k: int) -> float:
    """Share of the nuggets with at least one supporting document in the top k."""
    top = set(ranked[:k])
    return sum(1 for nugget in nuggets if nugget & top) / len(nuggets)


def alpha_dcg(ranked: list[str], nuggets: list[set[str]], k: int) -> float:
    """Sum of the gains of the top k, each divided by log2(rank + 1) so higher places count more.

    A document's gain is 1 per nugget it supports, but every earlier document that
    already supported that nugget multiplies it by (1 - alpha): repeats count for less.
    """
    times_covered = [0] * len(nuggets)
    total = 0.0
    for rank, doc_id in enumerate(ranked[:k], start=1):
        gain = 0.0
        for i, nugget in enumerate(nuggets):
            if doc_id in nugget:
                gain += (1 - config.EVAL_ALPHA) ** times_covered[i]
                times_covered[i] += 1
        total += gain / math.log2(rank + 1)
    return total


def ideal_ranking(nuggets: list[set[str]], k: int) -> list[str]:
    """The best possible top k: at every place, take the document that adds the most gain."""
    remaining = sorted(set().union(*nuggets), reverse=True)  # on a tie the last id wins, like the ndeval tool FreshStack uses
    times_covered = [0] * len(nuggets)
    ideal = []
    while remaining and len(ideal) < k:
        def gain(doc_id: str) -> float:
            return sum((1 - config.EVAL_ALPHA) ** times_covered[i] for i, nugget in enumerate(nuggets) if doc_id in nugget)
        best = max(remaining, key=gain)
        remaining.remove(best)
        ideal.append(best)
        for i, nugget in enumerate(nuggets):
            if best in nugget:
                times_covered[i] += 1
    return ideal


def alpha_ndcg(ranked: list[str], nuggets: list[set[str]], k: int) -> float:
    """Our alpha-DCG divided by that of the ideal ranking, so 1.0 is a perfect top k."""
    return alpha_dcg(ranked, nuggets, k) / alpha_dcg(ideal_ranking(nuggets, k), nuggets, k)


# Start of the evaluation: run every question of a split through the three searches, print the averages and save all scores.
def evaluate_retrieval(split: str, limit: int | None = None) -> None:
    """Run every question of the split through the three searches, print the averages and save all scores."""
    if not config.DB_PATH.exists():
        raise SystemExit("No database yet: run `uv run tka setup` and `uv run tka index` first.")
    # 1
    questions = load_questions(split)[:limit]
    vectors = question_vectors(questions)
    conn = database.connect()

    # 2
    per_question = {}
    for number, question in enumerate(questions, start=1):
        per_question[question["id"]] = {}
        for mode in MODES:
            ranked = [doc_id for doc_id, _score in search(conn, question["text"], mode, config.EVAL_RECALL_K, vectors[question["id"]])]
            per_question[question["id"]][mode] = {
                METRICS[0]: recall(ranked, question["nuggets"], config.EVAL_RECALL_K),
                METRICS[1]: coverage(ranked, question["nuggets"], config.EVAL_COVERAGE_K),
                METRICS[2]: alpha_ndcg(ranked, question["nuggets"], config.EVAL_NDCG_K),
            }
        print(f"  {number}/{len(questions)} questions done")
    conn.close()

    # 3
    averages = {
        mode: {metric: round(sum(scores[mode][metric] for scores in per_question.values()) / len(questions), 4) for metric in METRICS} #Wat?
        for mode in MODES
    }

    # 4 Printen
    print(f"\nRetrieval on {split} ({len(questions)} questions)")
    print(f"{'mode':<10}" + "".join(f"{metric:>15}" for metric in METRICS))
    for mode in MODES:
        print(f"{mode:<10}" + "".join(f"{averages[mode][metric]:>15.3f}" for metric in METRICS))

    if limit:
        print("\nTest run with --limit: results not saved.")
        return
    results = {
        "split": split,
        "questions": len(questions),
        "settings": {
            "embed_model": config.EMBED_MODEL,
            "query_embed_model": config.QUERY_EMBED_MODEL,
            "fusion": "score fusion (each list scaled to 0..1, then weighted sum)",
            "semantic_candidates": config.SEMANTIC_CANDIDATES,
            "keyword_candidates": config.KEYWORD_CANDIDATES,
            "weight_semantic": config.WEIGHT_SEMANTIC,
        },
        "averages": averages,
        "per_question": per_question,
    }
    # Date and time in the name, so every run is kept and none overwrites an earlier one
    path = config.RESULTS_DIR / f"retrieval-{split}-{datetime.now():%Y-%m-%d-%H%M}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"\nSaved to {path}")
