# Cypher 9.6.0 — Document answers and extractive summaries

Core Preview 9.6.0; Python distribution 0.9.6a1. 15 September 2026.

The user verified 9.5.1 on Windows: filename search found `Documents/meeting-notes.txt`, and the
text reader displayed all 101 bytes with digest
`b34d7c4d918b91e06a6538704525d9432227285c433d778d8e0f814084f55f02`.
That proves the corrected Windows read comparison on the demonstrated file; it does not generalize
to every filesystem or prove every cancellation race. These checks need not be repeated.

## Changes

- Adds a native `Docs:` route for an explicitly selected granted text file, with ask and summarize
  commands. No model-generated instruction can dispatch it.
- Uses the proven 9.5.1 byte-reader through a shared helper. The independent path/handle timestamp
  comparisons, identity/size checks, UTF-8 validation and cancellation behavior are retained.
- Supplies a bounded selection of line segments to one installed local-model generation. The
  model can select up to four known IDs; generated prose, unknown IDs and truncated output fail.
- Displays only original source quotes with checked IDs, line references, byte digest, snapshot
  time and coverage information. Summary output is explicitly labelled extractive.
- Reuses the existing fixed-loopback transport and local-model checks. No new network provider,
  model download, automatic retry, cloud inference route, embedding model or private-file index.
- Uses a separate pinned `document_worker.pyz` under the existing owned-process lifecycle. Its
  package excludes the file action engine, action-task dispatcher and public research worker.
- Native progress, Stop, busy-state gating and confirmed-exit handling use the existing local
  worker slot. A document worker may emit terminal results only; it cannot request action approval.
- The installer checks the document package hash and executes a real temporary file/grant fixture
  with fake model responses before replacing the resident host. Live model generation is not an
  installation prerequisite.

Ollama's official [Generate API](https://docs.ollama.com/api/generate) supports a system prompt,
non-streaming response, thinking settings and JSON-schema format. Its
[structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs) recommends
validating generated data. Cypher additionally checks every selected ID against its offered snapshot.

Quote integrity does not prove relevance, entailment, completeness or source truth. This release
deliberately presents selected source passages rather than a generated paraphrase. A no-selection
or partial-coverage result is not evidence that the full document lacks an answer. The native
view and Copy remain human-controlled; document text is excluded from chat history.

File apply/undo and permission engines, public research logic, runtime/model settings and Windows
workflow engines are retained. The new document call has its own bounded request settings; it does
not tune existing chat or research. No benchmark values were supplied for 9.4.0, so no performance
improvement, peak GPU memory or controlled cold/warm result is asserted.

One new Windows handoff is documented in DOCUMENT_ANSWERS_SETUP.md. Keep 9.5.1 for rollback.
