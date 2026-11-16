# Checklist

What the final solution needs. The "Required" part comes straight from [assignment.md](assignment.md). Tick items off as they are done.

## Required (from the assignment)

### Assistant

- [ ] Loads the LangChain corpus (`freshstack/corpus-oct-2024`, subset `langchain`) and makes it searchable
- [ ] Answers questions using retrieved information from the corpus only (no live web search)
- [ ] Cites the supporting corpus chunks by document ID (the original `_id`)
- [ ] Says clearly when the corpus does not contain enough information, instead of guessing
- [ ] Interactive command-line interface for asking new questions
- [ ] Queries dataset is never input to the assistant (not in the index, the prompt or examples)

### Evaluation

- [x] Questions split into a development part and a separate part for the final evaluation
- [ ] Retrieval quality measured
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

- [ ] Plain hybrid baseline first (BM25 + embeddings, merged with reciprocal rank fusion), measured before adding anything else
- [ ] Flat index: one embedding per corpus row (no extra chunking); every row fits whole in Cohere Embed
- [ ] "Not enough information" base layers: retrieval cutoff before the LLM, system prompt rule, citation check after the answer
- [ ] Dev/test split is reproducible (fixed seed, split saved in the repo); test part is not used for tuning. Ratio: 1/3 dev (68 questions), 2/3 test (135 questions)
- [ ] Small hand-written set of out-of-scope questions to test the "I don't know" behaviour (the official set has almost none)
- [ ] Time and cost per question logged during evaluation, for the trade-offs in the report
- [ ] Works from a clean clone by following the README only
- [ ] No API keys in the repo (`.env.example` instead)
- [ ] Use `freshstack/queries-oct-2024` (the assignment's "freshstacko" is a typo)

## Aftercare (easy to set up, use and understand)

- [ ] Setup takes a few commands: install, get the index, start the CLI
- [ ] Works with sensible defaults; settings go through `.env` or flags and are documented
- [ ] CLI has `--help` and the README shows a short usage example
- [ ] Clear error messages for the common problems (missing API key, missing index)
- [ ] Documentation lives in the repo: README for setup, run, approach and results; `Docs/` for background

## Optional (only if the above works and there is time)

- [ ] Support score with a tunable threshold and a retry loop
- [ ] Overseer for evaluation (a slow, thorough LLM that fact-checks the outputs on a subset)
- [ ] Language and version handling: tag chunks with language, repo, package and doc type (docs, code, notebook, test), read from the metadata (`_id` path and `url`) during chunking; soft boost for the question's language
- [ ] Smart chunking compared against the flat index: split rows on headings and code boundaries, every sub-chunk keeps its parent `_id`, cite and evaluate on the parent, each parent cited once
- [ ] Document context in each chunk, compared against the baseline: Voyage context-4 (own chunks grouped per document) or Anthropic-style contextual retrieval (an LLM writes a context line per chunk)
- [ ] Chunk enrichment (keywords, generated questions, context summary), compared against the baseline
- [ ] MCP server on top of the same search, so an existing agent can use it
- [ ] Local option: local embedding model with a SQLite index
- [ ] Filter boilerplate (licences, code of conduct) out of the index. Default is to leave it in; only filter if measuring on the dev questions shows it helps
