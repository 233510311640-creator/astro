# Cypher 9.8.0 validation — Grounded Document Answers

## Automated gate

- 528 automated tests run: 527 passed and one existing Windows-only skip;
- 27 focused document tests pass, including exact quotes, grounded sentences, sentence citations,
  insufficient evidence, malformed schemas, unknown/unused IDs, unsupported numbers, unrelated
  wording, URLs, multiline output, grant revocation, Stop and isolated-package execution;
- the offline native fixture reads a temporary granted file and validates a cited model draft using
  a fake local-model response;
- the installer must compile the native host, run the WPF/workflow/file/runtime/document self-tests
  and verify all pinned worker/artwork hashes before replacing the live host.

Completed on 18 September 2026: the native Windows host compiled, its self-test returned success,
and the real WPF tree rendered to `docs/cypher-grounded-documents-preview.png`. The render visibly
includes the new **03 DOC ANSWER** shortcut, scalable title controls and pinned signal artwork.

## Live handoff

After installation, press **Ctrl+Alt+Space**, choose **DOC ANSWER**, and complete the command using an
existing granted UTF-8 text file. Confirm the result visibly contains:

1. **Grounded document answer (model draft)**;
2. one or more short answer sentences ending in passage citations such as `[P1]`;
3. **Exact supporting passages** with matching IDs and source line numbers;
4. the explicit warning that grounding checks do not prove entailment.

A `PARTIAL` result with no answer is valid when the selected excerpts do not support the question.
Preserve that result; do not retry or switch models solely to obtain a more fluent answer.
