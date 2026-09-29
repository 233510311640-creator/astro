# Cypher 10.0.0 — Local Document Workspace

## Install

1. Keep the complete 9.9.0 package for rollback and finish any active task.
2. Extract the complete 10.0.0 package into a new folder.
3. Run **INSTALL_CYPHER_DOCUMENT_WORKSPACE.cmd** normally.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 10.0.0 / MONOCHROME SIGNAL**.

## Search document contents

Select **03 DOC SEARCH** and complete:

```text
Docs: search my-folder : project deadline
```

Cypher scans a bounded portion of supported UTF-8 text files in that approved root. It does not call
a model or create an index. Results show exact bounded excerpts, paths, line numbers and file digests.

## Work with larger text files

`Docs: ask`, `Docs: answer` and `Docs: summarize` now accept an explicitly named supported text file
up to 1 MiB. Evidence sent to the model is still limited to 4,096 passage-text bytes. The normal
`Files: read` display remains capped at 32 KiB.

## Compare two to four files

```text
Docs: compare my-folder "first.txt" with my-folder "second.txt" with archive "third.txt" : What changed?
```

Every file must already be inside a root with `read_text` permission. A non-empty comparison must
cite at least one passage from every supplied source. Two canonical references to the same file are
rejected. The model runs at most once.

PDF, Word/Office documents, indexing, embeddings, automatic file selection, public requests, file
changes and durable document memory remain unavailable. See `RELEASE_NOTES_DOCUMENT_WORKSPACE.md`,
`SECURITY_DOCUMENT_WORKSPACE.md` and `VALIDATION_DOCUMENT_WORKSPACE.md`.
