> Historical notes for 9.0.4. Its target-PC run removed the unrelated limitation and kept relevant
> previews, but still turned an HTTP-specific `urlopen` case into unqualified general behavior. The
> current candidate is 9.2.4; use [current setup](RESEARCH_PREVIEW_SETUP.md).

# Core Preview 9.0.4 — focused qualified research answers

Package v0.9.0.4 · Python package 0.9.0a5 · 30 August 2026

## Starting evidence

The user's 9.0.3 installation and focused two-source run established the native route, public-page
reader, two-source synthesis, reader-assigned citations and explanatory previews on the target PC.
The first attempt returned `MODEL_UNAVAILABLE`; the unchanged request then completed with two
sources and two findings, so this release does not add an automatic retry.

The completed result exposed one remaining answer-selection problem. The `urlopen` finding described
an "actual network operation" and emphasized HTTP/HTTPS without the documented returned-response
distinction or the broader URL cases shown later in the same definition. It also added an unrelated
error-handling limitation even though the question did not ask for errors or limitations. The
previews themselves were corrected: both showed relevant definition text.

The complete private prompt and raw model response were not collected. The regression fixtures model
the observed documentation structure and output class; they are not presented as a replay.

## Changes

- Group selectable passages by their existing reader-validated definition context. Match named
  contexts to identifiers in the question, then put a direct description, general return/result
  passage and contrasting case-scope passage first in the same evidence payload.
- Mark those groups and facets as navigation cues only. They cannot be cited, do not add facts and
  do not bypass the original source, offset, passage-kind or exact-quotation checks.
- Tell the existing local model to inspect the rest of a focused group when needed and preserve
  distinctions between cases instead of presenting one protocol case as the callable's whole scope.
- For a direct question, require an empty model-limitations list unless the question explicitly asks
  for limitations, caveats, risks, errors, uncertainty or a related facet. The worker still validates
  the complete returned list; a malformed value fails closed, while a valid unrequested tangent is
  omitted from the displayed report after validation.
- When several already-selected supports exist, let return/result wording prefer a return/result
  excerpt preview. The preview remains an exact, contiguous, at-most-25-word slice of selected
  evidence and is still only a display heuristic.

There is still one local-model generation per request. No retry generation, semantic-repair call,
API-specific answer template, arming delay, approval card, model download, search provider, Windows
action or file authority is added.

## Verification

- Python 3.12.13: 340 tests discovered; 339 passed and one Windows-only compiler test was skipped.
- All 117 research tests pass. Seven focused-answer regressions cover named-definition grouping,
  recommended description/return/case evidence, deterministic bounds, cue non-authority, return
  preview selection, explicit limitation intent and fail-closed malformed limitations.
- The full suite passes with `Path.read_text` defaulted to Windows CP1252. The research suite passes
  with default-encoding warnings treated as errors.
- The original public-network policy, fixed loopback model transport, extraction, passage resolution,
  exact-quotation validation and report protocol retain their security bounds. Existing Windows
  workflow files are unchanged; native research integration changes only its pinned worker hash,
  with host and installer version labels advanced to 9.0.4.
- Native compilation/self-tests remain mandatory installer gates. Linux fixtures cannot prove the
  real Qwen wording, Windows UI behavior or live public-page response.

These checks improve evidence placement and suppress an unrequested model tangent; they do not add a
semantic entailment verifier. Citation matching proves source provenance, not that every paraphrase
is true or complete. The unchanged focused comparison remains the real-model acceptance check.

## Target-PC check

Keep the working 9.0.3 folder/ZIP. Extract this package into a new folder, run
`INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, and confirm **CORE PREVIEW 9.0.4**.
With Ollama running and Auto selected, repeat the exact two-source block in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md).

The answer should distinguish a parsed-rules permission decision from opening a URL or request and
returning a response object. It must not call every supported URL case a network operation or imply
that HTTP/HTTPS is the complete scope. Because this question does not ask for limitations, no
unrelated error-handling limitation should appear. The source previews should remain explanatory;
the `urlopen` preview should preferably show selected return/result evidence.

No workflow, approval, Stop-race or model-installation retest is required. Send the completed answer
and both previews, or the visible diagnostic if the unchanged request does not complete.

Primary reference pages: [RobotFileParser](https://docs.python.org/3.12/library/urllib.robotparser.html)
and [urllib.request](https://docs.python.org/3.12/library/urllib.request.html).
