# Cypher 10.2.0 release notes - Bounded Office Documents

## Added

- Explicit DOCX, PPTX, and XLSX support for Docs ask, answer, summarize, and compare.
- Exact Word paragraph, PowerPoint slide/line, and Excel sheet/row evidence labels.
- A deterministic standard-library-only Office parser archive, integrity-pinned independently from
  the document worker and PDF parser.
- Path-free byte handoff to the Office parser under the existing two-process document job limit.
- Strict package type matching so renaming a DOCX to PPTX or XLSX fails closed.

## Safety and resource limits

The parser rejects legacy and macro-enabled formats, encryption, traversal names, duplicate names,
unsupported compression, XML declarations with DTD/entities, oversized parts, excessive entries,
expanded archives, extreme compression ratios, excessive XML elements, and malformed relationships.
It never evaluates formulas or macros and has no network, model, permission-store, file-action, or
path context.

Each Office file is limited to 8 MiB. Extracted output is limited to 1,000 units, 64 KiB per unit,
1 MiB total text, and a 2 MiB parser response. Parsing has a 20-second deadline and observes Stop.

## Retained behavior

The 10.1.1 registered HTTPS route, 10.1.0 PDF support, text-document workspace, file operations,
research, runtime diagnostics, approvals, Stop/recovery and Monochrome Signal UI remain.
