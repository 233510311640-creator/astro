# Cypher 10.2.0 - Bounded Office Documents

Cypher can now use explicit local **DOCX**, **PPTX**, and **XLSX** files in the existing document
commands. Keep the complete 10.1.1 package for rollback, then run
**INSTALL_CYPHER_OFFICE_DOCUMENTS.cmd** normally.

Open Cypher with **Ctrl+Alt+Space** and confirm
**CORE PREVIEW 10.2.0 / MONOCHROME SIGNAL**.

## Examples

```text
Docs: ask work "proposal.docx" : What delivery date is promised?
Docs: summarize work "quarterly-review.pptx"
Docs: answer work "forecast.xlsx" : What is the approved budget?
Docs: compare work "plan.docx" with work "status.pptx" : What changed?
```

`work` must already be a named folder grant with read permission. The command accepts one explicit
file for ask, summarize, or answer and two to four explicit supported files for compare.

## Boundaries

- Office files are limited to 8 MiB each.
- Only modern, non-macro OOXML formats are accepted: `.docx`, `.pptx`, and `.xlsx`.
- Legacy `.doc`, `.ppt`, and `.xls`, password-protected/encrypted packages, and macro-enabled files
  are rejected.
- A separate integrity-pinned process receives the file bytes, but no path, question, folder grant,
  model connection, network client, or action engine.
- Archive entry count, expanded size, per-part size, compression ratio, XML element count, extracted
  unit count, extracted text, response size, and parse time are bounded.
- Word evidence uses paragraph references, PowerPoint evidence uses slide/line references, and Excel
  evidence uses sheet/row references. Excel shows stored cell values; formulas are not evaluated.
- Search remains plain-text only. Images, charts, speaker notes, formatting, comments, tracked-change
  semantics, embedded files, and OCR are not interpreted.
- Extracted text is untrusted data. It cannot approve actions, execute formulas/macros, change files,
  access the network, or enter chat history.

The existing 4,096-byte model-evidence limit and at-most-one local generation remain unchanged.
