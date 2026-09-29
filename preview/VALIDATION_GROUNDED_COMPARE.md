# Cypher 9.9.0 validation — Grounded Two-Document Compare

## Automated gate

- 33 focused document tests pass;
- the complete suite runs 534 tests: 533 pass and one existing Windows-only test is skipped;
- successful comparison tests require both source labels, exact quotes, line references, digests and
  a single generation;
- adversarial tests cover one-sided/forged citations, duplicate source selection, empty files,
  empty evidence, balanced per-source budgets, independent grant revocation, Stop, malformed model
  envelopes, unsupported numbers, unrelated wording and isolated-package execution;
- the offline native fixture compares two temporary granted files using a fake model response and
  sends no live model or public-network request;
- the native Windows host compiles and its complete self-test passes;
- the real WPF tree renders to `docs/cypher-grounded-compare-preview.png` with **04 DOC COMPARE**,
  **05 NEW CHAT** and **06 COPY OUTPUT** visible in the system rail;
- the transactional installer completed on 18 September 2026, including every packaged safety
  group, native/worker self-test, pinned-hash check and Hermes capability check before replacement;
- the live host reports `ready` as `0.7.0-core-preview9.9.0`, and its installed document/file worker
  hashes match this package.

## Focused live handoff

After installation, press **Ctrl+Alt+Space**, select **04 DOC COMPARE**, and name two existing
granted UTF-8 text files. Confirm the result contains:

1. **Grounded two-document comparison (model draft)**;
2. one or more short sentences with source-scoped citations such as `[A-P1, B-P2]`;
3. separate Source A and Source B snapshot/digest information;
4. **Exact supporting passages** with matching source labels and line numbers;
5. the warning that grounding checks do not prove entailment.

A `PARTIAL` result with no comparison is valid when the bounded excerpts do not support one. Keep
that result; do not retry or switch models solely to obtain a fluent comparison.
