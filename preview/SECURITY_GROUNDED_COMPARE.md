# Grounded two-document comparison boundary — 9.9.0

`Docs: compare` is an explicit native command, not a general chat capability. The person names two
existing granted roots/files and one question. Cypher does not enumerate, index, remember, infer or
automatically select either file.

Each file passes the existing verified bounded reader independently. Each snapshot is valid UTF-8,
uses an approved text extension and is at most 32 KiB. The first file is Source A and the second is
Source B. The model receives source labels, source-scoped passage IDs, line numbers, bounded passage
text and the question. It does not receive roots, paths, filenames, other files, chat history,
credentials or action state.

Evidence is balanced: each source contributes at most six passages and 2,048 passage-text bytes,
with 4,096 passage-text bytes combined. Both grants are checked immediately before any excerpts are
sent to loopback Ollama and immediately before results are displayed. Revocation of either grant at
either boundary rejects the request. Stop suppresses final text and closes the owned worker; an
already submitted generation may still finish inside the shared Ollama service.

The model has no tools and returns the existing strict grounded-answer JSON schema. A non-empty
comparison is accepted only when its selected/referenced passages include both source labels. All
selected IDs must be referenced, and every answer sentence must cite one or two selected IDs.
Unknown fields, remote aliases, mismatched/incomplete generation, tool calls, forged/duplicate IDs,
unsupported numbers, URLs, code fences, multiline/control text and unrelated wording reject. Empty
arrays produce a partial result without claiming that no relationship exists.

These checks do not prove entailment, completeness, source truth or study quality. Generated text is
labelled a model draft and every cited exact passage is shown. Source content remains untrusted data
and cannot grant permission, start an action or alter the schema.

The isolated document bundle still excludes file mutation and public-research engines. This is an
application boundary within the signed-in user account, not an OS sandbox against arbitrary
same-user tampering. Results remain memory-only and outside chat history. No public network, paid
API, upload, index, embedding store, file change, new grant, retry or model substitution is added.
