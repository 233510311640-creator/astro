> Historical notes for 9.0.3. Its target-PC run corrected the previews but still overgeneralized
> `urlopen` and added an unrelated limitation. The current candidate is 9.2.4; use
> [current setup](RESEARCH_PREVIEW_SETUP.md).

# Core Preview 9.0.3 — research evidence and qualifications

Package v0.9.0.3 · Python package 0.9.0a4 · 28 August 2026

## Starting evidence

The user's 9.0.2 screenshot shows a completed two-source request with two distinct findings.
That establishes the focused comparison pipeline on the target PC, not the quality of every claim.
The first preview still starts in module-level introductory material; the second shows a function
signature. The urlopen finding describes retrieving content through HTTP without distinguishing
the returned response object or the documented support for other protocols.

The complete private draft and original passage catalog are unavailable. The new regressions use
explicitly synthetic HTML with the same structural problem, not a claimed replay of that draft.

## Changes

- Preserve visible paragraph, definition, heading and code-block boundaries, including a
  `role="main"` documentation body. Inline markup stays joined. Hidden content and heading
  permalink controls are excluded; body-byte SHA-256 remains based on the original response.
- Give explanatory definition passages their nearby reader-derived term/signature as context.
  Headings, signatures and source-code metadata are labels, not selectable supporting passages.
  Code examples remain available and are labeled separately from prose.
- Keep each 12–240-character passage inside one structural block, prefer sentence boundaries and
  flag cut fragments. At most 48 passages per source remain available. When there are more,
  deterministic question/context relevance selects a bounded subset in document order and the
  report discloses the bound. Extraction remains limited to 8,000 characters per source.
- Send the existing model compact, deduplicated context labels in the same single generation.
  Ask it to preserve return types, conditions, exceptions, negation and protocol/version scope;
  distinguish returned objects from readable content; and describe missing information as a
  limit of the read excerpts rather than a claim about the entire page.
- Prefer explanatory selected evidence over signature-like or introductory text in the preview.
  Never replace a selected quote with an unselected explanation or rewrite the quote. Preview
  ranking is structural/lexical, not a semantic verifier. Identical quote text with ambiguous
  contexts does not receive a guessed context label.
- Revalidate block offsets and context provenance before any model request. Selected passage
  kind/context/fragment metadata must still match the reader's catalog. Context IDs cannot be
  cited as passage IDs. The existing exact-quote validator and conservative duplicate rules remain.

There is no hardcoded answer for these Python APIs, extra model call, retry, repair generation,
arming delay, new approval card, model download, search provider or permission expansion.
The Windows workflow files are byte-identical to 9.0.2. Native research lifetime/Stop code changes
only in its pinned worker hash; host and installer changes otherwise only update version labels.

## Verification

- Python 3.12.13: 333 tests discovered, 332 passed, one Windows-only compiler test skipped.
- All 110 research tests pass, including 24 new structural-evidence regressions. These cover
  signature/intro preference, qualifications in model evidence, nested/hidden definitions,
  inline code, exact offsets, fragments, bounds, forged context, source-ID isolation,
  invalid-input rejection before model requests and the complete mocked two-source pipeline.
- The full suite also passes with `Path.read_text` defaulted to Windows CP1252. Research tests
  pass with default-encoding warnings treated as errors. No encoding or safety gate is skipped.
- Network policy, local transport, exact-quotation validation, rendering protocol and the main
  research flow retain their previous ASTs. Native workflow code and the installer entry point
  are unchanged; integration changes are limited to version labels and the worker hash.
- Native compile/self-tests, actual Windows UI behavior and real Ollama wording are not run in
  this Linux environment. The required native installer gates remain before host replacement.

These tests establish deterministic wiring and bounds, not that the model always chooses the
right evidence or preserves every qualification. Citation checks establish provenance, not truth,
relevance or entailment. The one focused real-model comparison remains the acceptance check.
Live research Stop/exit, rollback, repeated-run latency/VRAM and stronger OS containment remain
separate unverified gates. No new major capability is declared complete.

## Target-PC check

Keep the working 9.0.2 folder/ZIP. Extract this package to a new folder, run
`INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, and confirm **CORE PREVIEW 9.0.3**.
Use the same two-source question in [RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md), with
Ollama running and Auto selected. Do not change the question to hide the original regression.

Check that the answer distinguishes the parsed-rules permission decision from opening a URL and
returning a readable response object, without claiming HTTP is the only supported protocol.
Previews should show explanations, not just source-path metadata or signatures. A limitation about
missing evidence should refer to the read excerpts. No Stop race or old workflow test marathon is
needed. Send the answer and both previews, or the visible diagnostic if the result is partial.

Primary reference pages: [RobotFileParser](https://docs.python.org/3.12/library/urllib.robotparser.html)
and [urllib.request](https://docs.python.org/3.12/library/urllib.request.html).
