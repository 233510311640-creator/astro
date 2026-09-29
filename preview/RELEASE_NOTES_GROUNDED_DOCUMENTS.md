# Cypher 9.8.0 — Grounded Document Answers

Core Preview 9.8.0; Python distribution 0.9.8a1. 18 September 2026.

## What changed

Cypher adds an explicit grounded-answer command for one granted UTF-8 text file:

```text
Docs: answer ROOT "relative/file.txt" : your question
```

The route reads the named file again, supplies bounded excerpts to one verified installed local
model, and accepts at most four short answer sentences. Every sentence must cite one or two selected
passage IDs. Cypher then shows the generated sentence and the exact supporting source passages with
checked line references, snapshot time, byte count and SHA-256 digest.

The existing `Docs: ask` and `Docs: summarize` commands remain extractive and unchanged. A new
**DOC ANSWER** shortcut in the system rail fills the new command prefix without dispatching it.

## Grounding and rejection rules

- only IDs offered from the current read snapshot are accepted;
- every selected passage must support at least one displayed sentence;
- cited IDs must be unique and belong to the selected evidence set;
- numbers in generated prose must appear exactly in its cited passage text;
- each sentence must share meaningful source wording or a checked numeric value;
- URLs, code fences, multiline/control text, unknown fields and oversized output reject;
- empty evidence and empty answer arrays produce a truthful partial result;
- there is no retry, repair call, alternate model, download, public request or action tool.

These checks reduce unsupported output; they do not prove semantic entailment. The UI labels the
answer as a model draft and always places the exact evidence directly below it for human review.

## Preserved boundaries

One existing `read_text` grant is required before read, before local-model input and before display.
Folder paths and filenames do not reach the model. Document output remains outside chat history and
is not persisted. The pinned worker still excludes file-action and public-research engines. Stop,
worker containment, local-model verification, response limits and the Monochrome Signal UI remain.

No support for PDF, Office files, indexing, multiple-document comparison, public document upload,
automatic file selection or durable memory is added in this milestone.
