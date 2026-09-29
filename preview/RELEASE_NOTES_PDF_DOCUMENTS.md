# Cypher 10.1.0 - Bounded PDF Documents

Core Preview 10.1.0; Python distribution 0.10.1a1. 19 September 2026.

## What changed

Explicit `Docs: ask`, `Docs: answer`, `Docs: summarize` and `Docs: compare` commands can now use
PDF files already inside a folder with `read_text` permission. A request may mix PDF and supported
UTF-8 text sources. PDF evidence includes page and line references; the original PDF byte count and
SHA-256 snapshot digest remain visible.

PDF extraction runs in a separate integrity-pinned Python archive containing pypdf 6.10.0. The
parser receives only the verified PDF bytes through standard input. It receives no source path,
folder grant store, model connection, question, action engine or conversation. Its response is a
strictly validated page/text structure before evidence selection can begin.

## Fixed limits

- one explicitly selected PDF per ask/answer/summarize command;
- two to four explicit text/PDF sources per comparison;
- 8 MiB and 100 pages per PDF;
- at most 64 KiB extracted UTF-8 text from one page;
- at most 1 MiB extracted UTF-8 text from one PDF;
- 20 seconds for the parser child;
- 512 MiB process-memory ceiling inherited from the owned Windows job;
- unchanged 12-passage / 4,096-byte model-evidence ceiling;
- at most one installed-local-model generation and no retry.

Encrypted, malformed, oversized and over-page-limit PDFs reject before model access. Image-only or
scanned PDFs return no extractable text; OCR is not included. Folder-wide `Docs: search` remains
plain-text only and model-free.

## Preserved boundaries

The normal `Files: read` viewer remains UTF-8 text only and capped at 32 KiB. This release adds no
PDF modification, JavaScript execution, attachment extraction, form filling, OCR, Office parsing,
public request, saved index, model download, extra folder permission or action authority.

