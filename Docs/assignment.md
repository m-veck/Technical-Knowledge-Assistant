# AI ENGINEER TAKE-HOME ASSIGNMENT

## Technical Knowledge Assistant

### Overview

Build a retrieval-augmented generation (RAG) assistant that answers technical questions about LangChain.

The assistant should retrieve relevant information from the provided dataset, use it to answer the question, and cite its sources so users can verify the answer.

This is a prototype. We value a working solution, well-reasoned choices, and clear results over completeness or complexity.

### Dataset

Use the LangChain subset of the FreshStack October 2024 snapshot. It consists of two separate Hugging Face datasets, each with its own role:

- **Corpus (knowledge source):** [freshstack/corpus-oct-2024](https://huggingface.co/datasets/freshstack/corpus-oct-2024) (subset: langchain)

Documentation and source code from GitHub repositories, split into small chunks, each with a document ID. This is the only material the assistant may search.

- **Queries (evaluation data):** [freshstacko/queries-oct-2024](https://huggingface.co/datasets/freshstack/queries-oct-2024) (subset: langchain)

Real LangChain questions from Stack Overflow, each with a reference answer, nuggets (key facts a good answer should contain), and relevance judgments that link each question to the relevant corpus chunks. Use these only to evaluate your solution, never as input to the assistant.

### Your task

Build a working solution that:

- Loads the corpus and makes it searchable.

- Answers questions using retrieved information and cites the supporting corpus chunks by document ID.

- Says clearly when the knowledge source does not contain enough information, instead of guessing.

- Provides an interactive command-line interface for asking new questions.

- Evaluates retrieval quality, answer quality, and whether the citations support the answers.

You choose the models, tools, retrieval approach, and evaluation method. Explain your choices. Answers must be based on the provided corpus, not on live web search.

The questions are provided as a single set. Split them yourself: use one part during development and keep a separate part for the final evaluation. You may evaluate all remaining questions or a documented subset.

Report measured results, including examples of good and poor answers. Describe the main limitations and trade-offs, such as speed, cost, and answer quality.

### Practical notes

- You may use any LLM or embedding provider, including local models. We do not provide API credits.

### Deliverables

A GitHub repository containing:

- Working code, including the interactive CLI.

- Clear setup and run instructions.

- A short explanation of the approach and key decisions.

- Evaluation code and instructions to reproduce the results.

- A concise results report with example answers, evaluation findings, limitations, and lessons learned. The report may be part of the README.

### What we assess

- A working, reproducible solution.

- Useful answers backed by correct citations.

- Meaningful evaluation with honest results.

- Clear explanations of decisions and limitations.

*A more complex architecture does not earn extra credit by itself.*
