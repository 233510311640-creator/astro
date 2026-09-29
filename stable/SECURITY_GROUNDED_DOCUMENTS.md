# Grounded document boundary — 9.8.0

`Docs: answer` is a new explicit native input route, not a general chat capability. The person names
one existing granted root, one relative UTF-8 text file and one question. Cypher does not enumerate,
index, remember, infer or automatically choose document content for this route.

The existing bounded reader and permission checks run before file access. The same grant is checked
again immediately before sending excerpts to loopback Ollama and immediately before displaying the
result. Revocation at either boundary rejects. The file snapshot is limited to 32 KiB and the model
receives at most 12 line segments / 4,096 evidence bytes. Paths, filenames, other files, chat history,
credentials and action state are not included in the model prompt.

The model has no tools and returns strict JSON. Cypher validates the selected passage IDs, sentence
shape, cited support IDs, source-word overlap and exact numeric tokens. It rejects remote aliases,
model mismatch, incomplete generation, tool calls, unknown fields, duplicate/unknown/unused IDs,
URLs, code fences, multiline/control text and unsupported numbers. Invalid output ends the request;
there is no second generation, model substitution or repair prompt.

Lexical and numeric checks are not a proof of entailment or source truth. A fluent sentence can
still misstate a relationship while sharing source words. Therefore generated prose is explicitly
labelled a model draft and its exact source passages are always displayed. Users should verify the
draft against those quotes before relying on it.

Source text remains untrusted data. It cannot grant a capability, initiate an action or change the
response schema. The document package excludes file mutation and public research engines. This is an
application boundary inside the current-user account, not a hardened OS sandbox against arbitrary
same-user tampering.

Results remain memory-only in the native view and outside chat history. Copy requires a human click.
Stop suppresses final document text and closes the owned worker, although an already submitted local
generation may finish inside the shared Ollama service. No public network, paid API, upload, index,
embedding store, file modification, retry, persistent memory or new folder permission is added.
