# Document route boundary — 9.6.0

Human native input selects one root/path and ask/summarize command. No file enumeration,
automatic indexing, previous read reuse or generated action routing occurs. Existing root and
`read_text` grant checks precede the read, precede model input and precede final display. The reader
keeps the 9.5.1 independent stat/fstat snapshot checks and exact identity/size comparisons.

The runtime sends the question and bounded source excerpts only to fixed-loopback Ollama. Two
metadata calls verify the selected installed local model before one generation; no auth fields,
proxy, redirect, public endpoint, model pull, unload or alternate model is available on this route.
This trusts local Ollama's metadata and the same-user service, as the prior runtime route does.

Source text is untrusted data in a structured prompt. The model has no action tools and returns
only passage IDs. All displayed quote text and line locations come from the previously read bytes.
Unknown IDs, duplicated IDs, extra generated fields, incomplete output and model mismatch reject.
This does not guarantee semantic relevance or defeat all attempts to bias passage selection.

The worker package excludes `operator_engine.py`, `file_tasks.py` and `research_worker.py`.
Its included permission helpers are used only for read access in production. This is an
application boundary, not an OS filesystem/network sandbox against arbitrary same-user tampering.
The existing one-process Windows job, memory/output limits, isolated Python launch, pinned package,
nonce protocol, result-only frame check and confirmed exit still apply.

The selected-file reader performs actual bounded reads, validates type/encoding and rejects
ordinary identity/metadata changes. The report is a snapshot, not proof that the file remains
unchanged later. No claim is made that every adversarial filesystem race is prevented.

Stop closes the active client connection and suppresses final source text. An already submitted
generation may continue in the shared Ollama server; Cypher does not stop that shared service.
No generated prose, thinking or context is saved. Source quotes appear only in the current view,
outside chat history; Copy requires a human action. The offline installer self-test uses only
temporary synthetic files and fake model responses, without changing lasting folder permissions.
