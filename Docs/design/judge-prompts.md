# The judge prompts

The answers of the assistant are graded by an LLM judge. The judge is used for evaluation only: it sees the nuggets and the reference answers of the test set, the assistant never does.

The judge makes two calls per answer, each with its own prompt. They are separate so that one verdict cannot colour the other.

| | Call 1: nuggets | Call 2: support |
|---|---|---|
| Prompt | `src/tka/prompts/judge-nuggets-prompt.md` | `src/tka/prompts/judge-support-prompt.md` |
| Question it answers | Is the answer complete, and would it help? | Does the answer only say what its sources say? |
| What it sees | The question, the answer, the nuggets, the reference answer | The answer, its statements, the full text of the cited documents, the question (as context, not as a source) |
| What it returns | Per nugget `full`, `partial` or `none`; one overall verdict `helpful` | Per statement `supported`, `partly` or `not_supported`; a list of claims without a source |

Every verdict comes with a short reason, so a person can check the judge quickly.

## Call 1: nuggets

A nugget is one short fact that a good answer must contain. The nuggets come with the test set (FreshStack) and were taken from the accepted Stack Overflow answer.

What the prompt tries to do:

- **Compare meaning, not wording.** The assistant writes from its documents, so it rarely uses the words of the nugget.
- **Grade only what the answer says.** A fact the reader would have to look up does not count.
- **Keep completeness and usefulness apart.** An answer that solves the problem in another way misses the nugget, but can still be helpful. That is why there is a separate `helpful` verdict.
- **Not reward a polite refusal.** An answer that says "the documents do not cover this" is honest, but it is never graded as fully helpful.

What it deliberately does not see:

- **The documents.** This call compares the answer with the nuggets only.
- **Whether the search found a document for each nugget.** Code knows this from the labels of the test set. Telling the judge would push it towards "then the answer probably says it".

The reference answer is given as background, because a short nugget can be hard to read on its own. The prompt says that it is not graded and that style does not matter.

## Call 2: support

This call checks for hallucination: does the assistant say things its sources do not back?

What the prompt tries to do:

- **Judge by the documents only.** The judge may not use its own knowledge. A statement that is true but not in the documents counts as `not_supported`, because the reader cannot check it.
- **Check each statement against the documents it cites**, not against the others. Otherwise a statement could pass on a document that was never cited for it.
- **Catch claims outside the statements.** The judge also reads the full answer and lists every claim that no cited document backs, including code whose lines are in no document.
- **Not flag what is not a claim:** remarks about the documents themselves, what the answer says about the user's own code, data or error message, and a conclusion that follows directly from supported facts. The judge gets the question for this reason: in a first trial without it, most flagged claims were remarks about the user's own code.

What it deliberately does not see:

- **The retrieved documents that were not cited.** A claim that rests on one of those is listed as unsupported. That is strict on purpose: the reader of the answer cannot check it either.
- **The nuggets and the reference answer.** This call is about the sources, not about completeness.

## How the two calls are combined

Code, not the judge, puts the results together. Per nugget it has two facts:

- from the labels of the test set: was a supporting document among the ten retrieved?
- from call 1: does the answer say the nugget?

| Retrieved | In the answer | Meaning |
|---|---|---|
| yes | yes | found and used |
| yes | no | found, but not used: the answer step missed it |
| no | no | not found: the search missed it |
| no | yes | in the answer without a labelled document: from an unlabelled document, or from the model's own knowledge |

Unsupported statements and claims from call 2 are counted next to these.

Answers with an outcome other than `answered` get no judge calls: their nuggets count as not in the answer, and they have no statements to check.

## Known limits

- The judge is the same model as the assistant (Claude Sonnet 5.5), so it may be lenient on its own answers. A hand check of a sample of answers is the counterweight.
- The model has no temperature 0, so a rerun of the judge can give slightly different verdicts.
- The labels of the test set are not complete: a document that supports a nugget but was never labelled counts as "not found".
