# Checklist

What the final solution needs. The "Required" part comes straight from [assignment.md](assignment.md). Tick items off as they are done.

## Required (from the assignment)

### Assistant

- [x] Loads the LangChain corpus (`freshstack/corpus-oct-2024`, subset `langchain`) and makes it searchable
- [x] Answers questions using retrieved information from the corpus only (no live web search)
- [x] Cites the supporting corpus chunks by document ID (the original `_id`)
- [x] Says clearly when the corpus does not contain enough information, instead of guessing
- [x] Interactive command-line interface for asking new questions
- [ ] Queries dataset is never input to the assistant (not in the index, the prompt or examples)

### Evaluation

- [x] Questions split into a development part and a separate part for the final evaluation
- [x] Retrieval quality measured
- [ ] Answer quality measured
- [ ] Measured whether the citations support the answers
- [ ] Final evaluation run on the held-out part (all remaining questions, or a documented subset)
- [ ] Measured results reported, with examples of good and poor answers

### Repository and report

- [ ] GitHub repository
- [ ] Working code, including the interactive CLI
- [ ] Clear setup and run instructions
- [ ] Short explanation of the approach and key decisions (models, tools, retrieval approach, evaluation method)
- [ ] Evaluation code and instructions to reproduce the results
- [ ] Concise results report: example answers, evaluation findings, limitations, lessons learned (may be part of the README)
- [ ] Main limitations and trade-offs described: speed, cost, answer quality
- [ ] Sent in before Wednesday 18 November 2026, 08:00

## Needed to get there (my decisions)

Not literally in the assignment, but my own

### Index and retrieval

- [x] Flat index: one embedding per corpus row (no extra chunking); every row fits whole in Cohere Embed
- [x] Plain hybrid baseline first (BM25 + embeddings, merged with reciprocal rank fusion), measured before adding anything else
- [x] Fusion tuned on the dev part only: score fusion (0.7 semantic + 0.3 keyword) replaced rank fusion
- [x] Retrieval scores of every run saved in `results/`, so they can be inspected without rerunning

### Answer step (version 1)

- [x] One retrieval followed by one LLM call; no agent loop, no tools
- [x] Answer as structured JSON: the answer, the statements behind it with the full corpus `_id` per statement, and an `outcome` (answered, not in corpus, out of scope, about the assistant)
- [ ] Retrieval result saved per question (question, document IDs, scores, rank)
- [ ] Citation check in code: every cited `_id` must be in that question's retrieval result; the invalid-citation rate is reported
- [ ] "Not enough information" base layers: retrieval cutoff before the LLM, system prompt rule, citation check after the answer

### Evaluation

- [x] Dev/test split is reproducible (fixed seed, split saved in the repo); test part is not used for tuning. Ratio: 1/3 dev (68 questions), 2/3 test (135 questions)
- [ ] LLM judge for answer quality: which nuggets made it into the answer. The judge is evaluation only: it may see the reference answer and the nuggets, the assistant never does
- [ ] LLM judge for citation support: each claim checked against the chunks cited for it
- [ ] Failures sorted into buckets for the report: retrieval missed the chunks, chunks retrieved but not used, false refusal, claim not supported by its citation
- [ ] 5 to 10 answers checked by hand, to pick the good and poor examples
- [ ] 10 to 20 hand-written out-of-scope questions to test the "I don't know" behaviour (the official set has almost none)
- [ ] Time and cost per question logged during evaluation, for the trade-offs in the report

### Repository

- [ ] Works from a clean clone by following the README only
- [ ] No API keys in the repo (`.env.example` instead)
- [x] Use `freshstack/queries-oct-2024` (the assignment's "freshstacko" is a typo)

## Aftercare (easy to set up, use and understand)

- [ ] Setup takes a few commands: install, get the index, start the CLI
- [ ] Works with sensible defaults; settings go through `.env` or flags and are documented
- [ ] CLI has `--help` and the README shows a short usage example
- [x] Clear error messages for the common problems (missing API key, missing index)
- [ ] Documentation lives in the repo: README for setup, run, approach and results; `Docs/` for background