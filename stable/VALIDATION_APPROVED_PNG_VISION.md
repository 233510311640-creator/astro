# Validation — Cypher 10.11.0

The explicit vision unit tests cover one approved PNG, the exact local request payload, a model without vision support, malformed CRC, excessive dimensions, malformed commands, Stop, and permission revocation after inference. The document-worker self-test includes a synthetic one-pixel PNG.

- Python suite: 592 tests run, 591 passed, one existing platform skip.
- Native Windows host compiled and passed its WPF and workflow self-test.
- Owned research, file, runtime and document workers passed offline self-tests; the document self-test exercised the image route. Hermes authenticated run preflight passed.
- Installer completed transactionally. Resident heartbeat reports `ready` and `0.7.0-core-preview10.11.0`.
- Installed document-worker SHA-256 equals release pin `a266fd7a52cf08689090313b4f1a018ea143ba002c27ed2621e4c90474986099`.

The package's SHA-256 manifest covers 360 non-manifest files and verified with zero mismatches. No live user image or real vision-model inference was submitted during these checks. Model interpretations remain unverified by design.
