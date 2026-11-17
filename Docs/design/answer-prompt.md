# The answer prompt

Every question is answered with one search and one Claude call. The system prompt of that call is `src/tka/prompts/answer-system-prompt.md`. It is a plain text file, so it can be read and changed without touching Python. The call itself is built in `src/tka/answer.py`.

The prompt has one goal: an answer that comes from the retrieved documents and that a reader can check against them. Its first line says so: the model answers from the documents it is given, not from its own knowledge.

| Part of the prompt | What it is for |
|---|---|
| The documents | Tells the model what it is looking at and how far to trust it |
| The four outcomes | Makes the model sort every question into one of four kinds |
| How to answer from the documents | The rules for the answer text: sources, code, length |
| What you return | The three fields of the reply |

## The documents

This part describes the corpus in a few lines: an October 2024 snapshot of ten GitHub repositories, cut into pieces of documentation, notebooks, source code, tests and configuration files. It also explains that the id of a document is the path of its file followed by the position of the piece.

What it tries to do:

- **Give the model enough to judge a document.** A model that knows the corpus is a snapshot of ten named repositories can tell a question about them from a question about something else.
- **Say that the search is not perfect.** Some documents will be off topic and useful ones may be missing. The model is told this, so it does not have to treat all ten documents as relevant.
- **Mark the input as material.** Everything inside the document and question tags is material to work with, never instructions. `Docs/design/hardening.md` covers this rule.

The description is short on purpose. A file tree of the corpus was considered and left out: it is long and would be paid for on every call.

## The four outcomes

Every question gets exactly one outcome.

| Outcome | When | What the answer does |
|---|---|---|
| `answered` | About these libraries, and the documents cover it fully or partly | Answers from the documents, with sources |
| `not_in_corpus` | About these libraries, but the documents do not let the model answer at all | Says the corpus does not contain enough information, without a guess |
| `out_of_scope` | Not a question for this assistant: another topic, a request to drop the rules or do another task, or input it cannot make sense of | Says briefly what it can help with |
| `about_assistant` | About the assistant itself or about what the corpus contains | Answers briefly from the description in the prompt |

Two rules settle the cases in between:

- **A fact in a document does not make a question in scope.** A question about geography stays `out_of_scope` when a test file happens to mention the answer.
- **A question about how a library works is always a library question**, also when it is phrased as a question to the assistant, such as "do you know how agents work?". It goes to the documents.

There is no outcome for "partly answered". The model cannot know whether the documents are complete, so a third state would be a guess.

## How to answer from the documents

- **Use only what the documents say.** The prompt gives the reason: the reader must be able to check every statement, and the model's own knowledge of these libraries may not match the snapshot.
- **Answer the covered part and name the part that is missing**, instead of refusing because something might be missing.
- **Say when a document is about another language or library than the question.** The same feature often exists in Python and in JavaScript.
- **Mark the sources in the text.** A sentence that rests on a document ends with the number of that document, like [3]. The numbers stay out of code blocks, because a number in square brackets inside code looks like an index. The sentence that introduces the code carries the number.
- **Take code from the documents.** Code is allowed, new code is not.
- **Write in English, and as short as a complete answer allows.** The length rule is its own line, so it is easy to change.

The prompt contains no example answers.

## What it returns

| Field | Content |
|---|---|
| `outcome` | One of the four outcomes |
| `answer` | The full answer for the reader, with the document numbers when the outcome is `answered` |
| `citations` | The statements the answer rests on, each with the ids of the documents that support it. Empty for the other three outcomes |

The answer and the citations say the same thing twice, for two readers. The answer is for a person. The citations are for code and for the judge: each statement is one full sentence that can be checked on its own against the documents it names.

## The user message

The system prompt goes in the `system` field. The user message holds the ten best documents of the hybrid search, and then the question.

```
<documents>
<document index="1">
<source>the id of the document</source>
<document_content>
the text of the document
</document_content>
</document>
...
</documents>

<question>
the question as the user typed it
</question>
```

- **Documents first, question last.** This is the layout from Anthropic's prompting guide for long inputs.
- **The `index` is the rank in the search result.** It is the number the model puts in the answer.
- **The question has its own tag**, so the prompt can point at it as material.

## What the model deliberately does not get

- **Nothing from the evaluation queries dataset.** No questions, answers, nuggets or tags from it are in the prompt or in the index.
- **No web search and no tools.** The corpus is the only source.
- **No chat history.** Every question is answered on its own. `tka ask` says this when it starts. Without a step that rewrites the question before the search, earlier turns do not help the search and can pull the answer away from the current documents.
- **No search scores and no urls.** The model sees the rank, the id and the text of each document. The GitHub url is added to the source list afterwards, by code.

## Known limits

- "Use only the documents" is a prompt rule. Code cannot check it. The support call of the judge measures it afterwards (`Docs/design/judge-prompts.md`).
- A request that mixes a library question with something else can be declined as a whole. `Docs/design/hardening.md` has the measured cases.
- The model has no temperature 0, so the same question can get different wording and different citations on a second run.
- A follow-up question does not work. Without the earlier question there is nothing to search for.
