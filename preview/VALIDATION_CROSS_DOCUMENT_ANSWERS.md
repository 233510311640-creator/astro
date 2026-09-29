# Validation — Cypher 10.10.0

- Python suite: 587 tests run, 586 pass, one pre-existing platform-specific skip.
- Cross-document fixtures: mixed text/PDF/Office citations, one local generation, withheld unsupported drafts, no-generation no-evidence path, grant revocation before generation, bounded four-source / 4,096-byte evidence.
- Document worker's direct offline self-test: passed, including the new `answer-all` route.
- Native .NET Framework 4.8 host: compiled and passed `--self-test`, including WPF workspace layout and reminder persistence checks.
- Installer-owned workers: research, file, runtime and document self-tests passed. The document test exercised separate pinned parser children. Hermes authenticated run capability preflight passed.
- Installer completed transactionally. Resident heartbeat reports `status: ready` and `version: 0.7.0-core-preview10.10.0`. Installed document worker SHA-256 matches the release pin `f59f9cbdf30d8a3356c039b11f0ec8d54ed0bf5c2821161b5ffba172ad74a328`.
- The package's `SHA256SUMS` lists every included non-manifest file and was checked with zero mismatches.

The offline fixtures and worker self-tests do not establish that arbitrary local PDFs or Office files extract correctly, or that a model's cited prose is logically entailed by the quotes. The app displays partial coverage and the exact excerpts so the user can verify them. No live user-document question was submitted during this validation.
