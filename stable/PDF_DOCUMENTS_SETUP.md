# Cypher 10.1.0 - Local PDF Documents

Current bundle: **10.2.0 Bounded Office Documents**. Start with
[OFFICE_DOCUMENTS_SETUP.md](OFFICE_DOCUMENTS_SETUP.md); the PDF behavior below is retained.

## Install

1. Keep the complete 10.0.0 package for rollback and finish any active task.
2. Extract the complete 10.1.0 package into a new folder.
3. Run **INSTALL_CYPHER_PDF_DOCUMENTS.cmd** normally.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 10.2.0 / MONOCHROME SIGNAL**.

## Ask or summarize a PDF

Select **04 DOC ANSWER** or enter one of these commands:

```text
Docs: ask my-folder "reports/brief.pdf" : What deadline is stated?
Docs: answer my-folder "reports/brief.pdf" : What deadline is stated?
Docs: summarize my-folder "reports/brief.pdf"
```

The PDF must already be inside a folder with `read_text` permission. Ask and summarize display exact
selected passages. Answer may add a short local-model draft with citations, followed by the exact
page/line evidence.

## Compare PDFs and text

```text
Docs: compare my-folder "old.pdf" with my-folder "new.pdf" with notes "changes.txt" : What changed?
```

Use two to four explicit sources. A non-empty draft must cite every supplied source. The fixed model
evidence budget is divided fairly; adding files does not enlarge it.

## Limits

PDFs are capped at 8 MiB and 100 pages. Extracted text is capped at 64 KiB per page and 1 MiB total.
Encrypted, malformed or over-limit PDFs reject. Scanned/image-only PDFs have no OCR. `Docs: search`
still searches supported plain-text files only. PDF editing, forms, attachments, signatures, Office
documents, public conversion services and persistent indexing are unavailable.

See `RELEASE_NOTES_PDF_DOCUMENTS.md`, `SECURITY_PDF_DOCUMENTS.md` and
`VALIDATION_PDF_DOCUMENTS.md` for the complete boundary.
