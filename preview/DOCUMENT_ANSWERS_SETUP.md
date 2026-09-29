# Cypher 9.8.0 — Grounded local document answers

Ask a question about one selected text file and receive a short model-drafted answer with
per-sentence passage citations plus the exact source evidence. The earlier ask and summarize routes
remain extractive.

## Install and check

1. Keep your working 9.5.1 folder or ZIP for rollback. Finish any active task.
2. Extract the complete 9.8.0 ZIP into a new folder.
3. Double-click **INSTALL_CYPHER_GROUNDED_DOCUMENTS.cmd** normally. Windows may hide `.cmd`.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.8.0 / MONOCHROME SIGNAL**. Select **AUTO ROUTE**.
5. Send this exact question about the synthetic note already verified on your PC:

```text
Docs: answer desktop-demo "Documents/meeting-notes.txt" : Where should this sample move?
```

The result should label itself **Grounded document answer (model draft)**, cite a passage such as
`[P3]`, and show the exact matching quote and line below. A PARTIAL result with no selected passage
means the model did not identify support in its supplied excerpts; it is not proof that no answer exists.
If a diagnostic appears, send that result instead of reinstalling or repeating the request.

Your successful 9.5.1 file search and 101-byte text read are accepted. Do not repeat organization,
undo, permissions, search, read or timed Stop checks for this handoff. The installer itself runs
the existing file checks and a new temporary document fixture before replacing the resident host.
The installer fixture uses fake model responses and does not contact Ollama or another service.

## Commands

| Command | Result |
| --- | --- |
| `Docs: help` | Syntax and boundaries; no model call. |
| `Docs: answer ROOT "relative/file.txt" : question` | Up to four short model-drafted sentences, each citing one or two exact passages displayed below. |
| `Docs: ask ROOT "relative/file.txt" : question` | Up to four quoted answer passages selected by the local model. |
| `Docs: summarize ROOT "relative/file.txt"` | Up to four quoted summary highlights. |
| `Files: folders` | Existing grant names. |
| `Files: find ROOT "fragment"` | Find a filename before explicitly choosing its path. |

ROOT is the command name of an existing approved folder, such as `desktop-demo`. The relative
path must stay inside that folder and its grant must permit text reads. Docs never chooses a file
automatically or reuses previously displayed file content. Each request reads its explicitly named
file again. Auto/Fast uses the configured Fast model; Deep uses the configured Deep model.

## What reaches the model

Only the question, selected text passages, line numbers/IDs and response instructions go to local
Ollama at `127.0.0.1:11434`. Folder paths, filenames, other files and chat history are not included
in the model prompt. The report displays the path to identify the source for you.

The worker checks installed local GGUF metadata and rejects remote/cloud aliases before generation.
It makes at most one generation, with no retry, substitute model, download, forced unload, public
request, action tool or file modification. A successful request reads model metadata using two
local API calls before that one generation; this is not a claim of only one total HTTP request.

For answer, model output is restricted to known passage IDs and at most four single-line sentences,
each citing one or two selected IDs. Cypher rejects extra fields, unknown/duplicate/unused IDs,
unsupported numbers, URLs, code fences, control text, incomplete generation or a mismatched model.
Quotes come from the read snapshot, never from model wording. Lexical and number checks reduce
unsupported output but do not prove entailment; verify the draft against the displayed evidence.
Source text can influence relevance selection; it cannot authorize a file action or execute a command.

## Limits and partial coverage

- File: valid UTF-8, at most 32 KiB, existing safe text extensions: `.txt`, `.md`, `.csv`, `.json`,
  `.log`, `.rst`, `.yaml`, `.yml`. PDF, Office, binary and other encodings are not included.
- Question: one line, at most 1,000 UTF-8 bytes. Command: at most 4,096 characters.
- Evidence: at most 12 nonblank line segments, each at most 480 UTF-8 bytes, and 4,096 text bytes
  total. Long lines are split into separately identified segments of the same line.
- Ask ranks segments using question-word overlap, with source order breaking ties. Summary samples
  across the file. Both show PARTIAL whenever not all nonblank segments reached the model.
- Local generation: 8K context, 768 output-token ceiling, 90-second request budget. Fast/Qwen
  thinking is disabled; GPT-OSS uses low thinking. No second call repairs an invalid response.
- Up to four answer sentences and four selected passages are displayed. CRLF line endings are normalized; display controls
  are escaped. Snapshot time and byte digest identify the bytes read, not the file's future state.

File text and the answer remain in the current native view and are excluded from model conversation
history. Copy is a separate human action. Stop discards an unfinished result, blocks further
requests and waits for worker exit. An already submitted Ollama generation may still finish on
the shared server. A grant revoked before sending or before displaying results rejects the request.

See RELEASE_NOTES_GROUNDED_DOCUMENTS.md, SECURITY_GROUNDED_DOCUMENTS.md and
VALIDATION_GROUNDED_DOCUMENTS.md.
