# Cypher 10.0.0 validation — Bounded Document Workspace

## Automated gate

- 40 focused document tests pass;
- 67 combined document/file-reader/package tests pass, with one existing platform skip;
- the complete suite runs 541 tests: 540 pass and one existing skip;
- tests cover model-free nested content search, exact excerpts/digests, result limits, no index
  creation, revocation, 1 MiB/structure limits, late evidence in files larger than 32 KiB, two- to
  four-source comparison, fair evidence budgets, five-source rejection, duplicate aliases, forged
  citations, Stop and isolated package execution;
- the offline worker self-test performs a two-file grounded comparison and a model-free folder search
  over temporary data only;
- native compilation, the executable self-test and the real WPF preview render pass on Windows;
- the rendered 1,120 × 720 workspace shows all seven system-rail controls without clipping;
- the transactional installer reruns all required safety groups, compiles and self-tests the host,
  runs every offline worker fixture, stops 9.9.0 cooperatively and starts 10.0.0;
- the live heartbeat reports `ready` on `0.7.0-core-preview10.0.0`, and installed document/file
  worker SHA-256 digests exactly match this package.

## Focused live handoff

After installation, press **Ctrl+Alt+Space** and use **03 DOC SEARCH** on one existing approved folder:

```text
Docs: search my-folder : exact words to find
```

Confirm the report states that no model or saved index was used and shows paths, lines and snapshot
digests. A partial result is expected if a documented scan limit is reached.

For comparison, use **05 DOC COMPARE** with two to four files. A non-empty draft must show citations
and exact passages for every Source A through D that you supplied. Preserve a failure or partial
result; do not retry or switch models solely to obtain more output.
