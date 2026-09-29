# Cypher 10.1.0 validation - Bounded PDF Documents

## Completed gates

- 47 focused document/PDF tests pass;
- 69 combined document and verified-reader tests pass;
- valid PDF extraction, page citations and mixed text/PDF comparison pass;
- malformed, encrypted, oversized and 101-page PDFs reject without model access;
- per-page and total extraction ceilings, parser hash tampering, Stop and text-only folder search pass;
- the self-contained parser imports under `-I -S` with no site packages and produces no stderr;
- document and file worker archives match their source and native SHA-256 pins;
- the native Windows host compiles and passes its executable self-test;
- the owned native document job successfully starts exactly one pinned parser child and completes a
  real PDF fixture while remaining inside the process limit;
- the 1,120 x 720 WPF preview renders without clipping or overlap;
- the complete regression suite runs 549 tests: 548 pass and one existing direct-run Windows
  platform check is skipped; the required Windows-native installer gates pass separately;
- transactional installation passes, the resident host reports READY on
  `0.7.0-core-preview10.1.0`, and the installed document, PDF-parser and file-worker hashes exactly
  match this package.

The previous 10.0.0 package remains the immediate rollback release.

## Focused live handoff

After installation, place a small text-based PDF inside an existing approved folder and use:

```text
Docs: ask my-folder "relative/report.pdf" : What is the stated deadline?
```

A successful result shows the PDF byte count and digest plus exact evidence with page and line
references. `PARTIAL` is valid when selected excerpts do not support the question. An image-only PDF
should state that no extractable nonblank text was found; do not retry it expecting OCR.

Preserve a parser diagnostic rather than weakening the limits, adding a password, switching to an
online service or repeatedly resubmitting the same file.
