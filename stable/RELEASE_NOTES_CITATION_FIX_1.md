> Historical notes for the 9.0.1 citation correction. Its focused one-source target-PC check subsequently passed. The current candidate is 9.2.4; use [current setup](RESEARCH_PREVIEW_SETUP.md).

# Core Preview 9.0.1 — research citation correction

Package v0.9.0.1 · Python package 0.9.0a2 · 28 August 2026

## What the target-PC result established

Ollama 0.32.13 is reachable. The configured Fast model, `qwen3.5:9b-q4_K_M`,
completed the research response after the Python documentation page was read.
Citation Check 2 identified the first rejection at finding 2, support 1: a
147-character quote was not an exact substring of the source. Removing differences
in case, spaces or backticks did not produce a match. The actual rejected wording
was not collected, so it is not reproduced or treated as a known paraphrase here.

The earlier connection-refused issue was resolved before this code change. This
release does not install or start Ollama, change its settings or replace its models.

## Correction

The reader now assigns IDs to bounded passages extracted from each supplied page.
The local model returns finding text and selects passage IDs. Cypher retrieves
quotation text directly from those source slices; it no longer asks the model to
copy quotation text into its response.

Each passage carries its source identity and character offsets. The output schema
allows only IDs from the current request's catalog, and the same schema is included
in the prompt. A separate deterministic check rejects unknown or duplicate IDs,
stale/altered passage bindings, old free-form quote fields, extra fields and duplicate
JSON keys. The resolved draft must still pass the original exact-quotation and
source-reference validator. There is no fuzzy matching, silent repair or second
generation. One finding is explicitly allowed when it answers the question.

`DRAFT_FORMAT_INVALID` and `PASSAGE_REFERENCE_INVALID` distinguish response format
and passage-selection failures. Failure reports now include a fixed diagnostic code
without printing the rejected model answer.

## Unchanged boundaries

- Existing local model selection, thinking setting, context/output limits and one
  generation per request. No model download, cloud fallback or paid API.
- Explicit public HTTPS URLs, checked network addresses, TLS and robots policy.
  No search engine, login, browser scripts or PDF capability added.
- Windows workflow code, one-time approvals, cancellation and process ownership.
  No arming countdown or additional approval step.
- Reports remain in memory. No research history, automatic saves, file/app actions
  or new broker permissions.
- Exact source references, 25 quoted words per source and 140 finding words per
  source remain the output bounds.

This correction establishes where excerpts came from. It does **not** prove that
the chosen passage supports every interpretation or that the source is true. A
model can still select an irrelevant passage or write an incorrect finding; the
report retains that limitation and important claims need review against the page.

## Verification

| Check | Result |
| --- | --- |
| Full Python regression suite | 288 discovered; 287 passed; one Windows compiler test skipped on Linux. |
| Research suite | 65 passed, including encoding warnings as errors and the Windows CP1252 source-read regression. |
| Reported failure class | Reproduced with a fixture containing an invalid 147-character second quote; catalog selection resolves exact source excerpts instead. This is not a replay of the unavailable original draft. |
| Original network, extraction, transport and exact-quote checks | AST comparison confirms they remain unchanged. |
| Native integration | Worker hash and version updated; host process controller and installer behavior retained. Native compilation and self-tests remain required installation gates. |
| Real local-model response with this correction | Pending target-PC acceptance. No local model is available in the build environment. |

## Install and test

Keep your earlier extracted packages for rollback. Extract this whole package to a
new folder and run **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally, not as
administrator. After success, press **Ctrl+Alt+Space** and confirm **CORE PREVIEW
9.0.1**. The existing interpreter, Hermes, Ollama and downloaded models are reused.

With Ollama running, select Auto and send:

```text
Research: What does RobotFileParser.can_fetch do, and what arguments does it take?
https://docs.python.org/3.12/library/urllib.robotparser.html
```

Expected: **RESEARCH COMPLETED**, at least one finding, `[S1]`, the actual source URL
and a supporting excerpt. Compare the finding to the source and send the Cypher
result screenshot. A partial result remains incomplete; share its diagnostic code.

Use Cypher's UI for this test. The older standalone Model/Citation Check packages
are pinned to 9.0.0 and intentionally will not run against the changed worker.
No Notepad/Calculator retest or Stop-button timing exercise is required here.

See [setup and rollback](RESEARCH_PREVIEW_SETUP.md) and
[security boundary](SECURITY_READONLY_RESEARCH.md).

The schema is sent both through `format` and in the prompt, following
[Ollama's structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs).
