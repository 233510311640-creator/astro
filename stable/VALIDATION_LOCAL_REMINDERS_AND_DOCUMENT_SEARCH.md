# Validation — Cypher 10.9.0

- Python suite: 582 tests run; 581 pass and one pre-existing platform-specific skip.
- Mixed-format search: unit fixtures cover text, PDF, DOCX, PPTX and XLSX hits; malformed PDF partial coverage; no model request or saved index.
- Native host: compiled against .NET Framework 4.8 and passed `--self-test`, including local reminder persistence, DPAPI protection, due delivery state, and WPF workspace layout.
- Worker packages: document and file `.pyz` archives rebuilt deterministically and pinned to their new SHA-256 digests. Research worker source was re-pinned after the version bump.
- Release integrity: `SHA256SUMS` and `SHA256SUMS.txt` list every included non-manifest file and verified with zero mismatches.

Installation and live 10.9.0 behavior are **not yet verified**. The normal installer stopped before changing the resident app because the current sandbox could not read the installed Ollama executable for its integrity check. A request to run the installer with the required access was rejected by the app's approval reviewer because its usage limit was reached; this was not a safety rejection of Cypher. Direct native owned-worker self-tests also could not complete in this restricted sandbox. The installed 10.8.0 host remains READY and unchanged.

When approval is available, run `INSTALL_CYPHER_LOCAL_REMINDERS_AND_DOCUMENT_SEARCH.cmd` from this package and confirm that the installer reports its native and owned-worker self-tests as passed, then check a READY heartbeat with version `0.7.0-core-preview10.9.0`. Do not delete or modify the existing 10.8.0 package to proceed.
