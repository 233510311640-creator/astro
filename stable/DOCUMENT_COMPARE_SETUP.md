# Cypher 9.9.0 — Compare two local text documents

Use one explicit question to compare exactly two text files that are already inside approved folders.

## Install and check

1. Keep the complete 9.8.0 package for rollback and finish any active task.
2. Extract the complete 9.9.0 package into a new folder.
3. Run **INSTALL_CYPHER_DOCUMENT_COMPARE.cmd** normally.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.9.0 / MONOCHROME SIGNAL**.
5. Select **04 DOC COMPARE** and complete the command with two files you intentionally choose:

```text
Docs: compare my-folder "first.txt" with my-folder "second.txt" : What changed?
```

The roots may differ when both already have `read_text` permission. Cypher does not search for or
choose documents automatically. The two file references must be different.

## Expected result

A successful result is labelled **Grounded two-document comparison (model draft)**. Its sentences
cite IDs such as `A-P1` and `B-P2`, and exact passages from both sources appear below. Each source
shows its path for you, snapshot time, byte count, digest and evidence coverage.

A partial result with no comparison is valid when the selected excerpts do not support the question.
If a diagnostic appears, keep that result rather than repeating the request or switching models.

## Boundaries

- each file must be valid UTF-8, at most 32 KiB and use an already supported safe text extension;
- each source supplies at most six bounded passages / 2,048 passage-text bytes;
- combined passage text is at most 4,096 bytes;
- at most four short comparison sentences and four selected supporting passages are displayed;
- at most one local generation runs, with no retry, repair or substitute model;
- paths and filenames identify the report for you but do not enter the model prompt;
- the result stays in the current view and outside chat history;
- no file modification, public request, index, automatic discovery, PDF/Office parsing or durable
  memory is added.

Grounding checks do not prove that a comparison sentence is logically entailed. Verify the draft
against the exact displayed passages. See `RELEASE_NOTES_GROUNDED_COMPARE.md`,
`SECURITY_GROUNDED_COMPARE.md` and `VALIDATION_GROUNDED_COMPARE.md`.
