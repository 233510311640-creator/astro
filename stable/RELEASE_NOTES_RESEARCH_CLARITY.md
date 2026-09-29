> Historical notes for 9.0.2. Its two-source request completed on the target PC, but excerpt quality and answer qualifications needed a follow-up. The current candidate is 9.2.4; use [current setup](RESEARCH_PREVIEW_SETUP.md).

# Core Preview 9.0.2 — clearer research findings and excerpts

Package v0.9.0.2 · Python package 0.9.0a3 · 28 August 2026

## Starting evidence

The user's 9.0.1 screenshot shows RESEARCH COMPLETED, one source read and three findings about
RobotFileParser.can_fetch. That focused source/model path passed. The third finding restated the
first, and the visible excerpt began with earlier setup methods instead of the requested method.
The screenshot does not expose the entire selected passage catalog or model draft, so regressions
model that layout problem with explicitly synthetic evidence rather than claiming a captured replay.

## Changes

- Ask for distinct findings, combine closely related supported details, avoid restated conclusions,
  and note only limitations that matter to the question. Comparisons must cite each source they use.
- Validate all draft items before filtering. Remove only identical cleaned, case-sensitive finding
  text with identical source/quote evidence, ignoring support order. Different evidence and different
  wording remain; this is not a synonym/semantic deduplication system. Exact duplicates no longer
  consume the 140-finding-word allowance per source. Empty/identical limitations are omitted.
- Number findings. For each cited source, choose one sentence-prefix excerpt from its selected
  evidence using finding/question word overlap. The preview is an exact contiguous slice, labeled
  with its finding number, with ellipses for omitted context. It can select a relevant later sentence
  instead of blindly displaying the passage's first 25 words.
- Keep long-sentence prefixes and basic abbreviation handling to reduce context-free clipping.
  The selection is a display heuristic, not a proof of relevance or entailment; a source passage
  may already begin mid-sentence. Only 25 quoted words per source are displayed, not all evidence.

There is still exactly one local generation per request. No second-pass repair, semantic merger,
automatic retry, arming delay, new approval step, model download, cloud fallback or search service
is added. Passage construction, request-specific ID/schema checks, source/offset binding, exact
quotation rules, network policy and model limits remain. Unknown/invalid references still withhold
all draft claims. Existing action approval, Stop and research process lifetime are not redesigned.

## Verification and limits

309 tests discovered: 308 passed, one Windows-only compiler test skipped. All 86 research tests
passed, including 21 added regressions for exact duplicates, preservation of different evidence/
numbers/negation/conditions, invalid repeated claims, source-bound excerpt selection, quoted-word
limits, Unicode, and two-source comparisons through the reader/model-ID/validator/render pipeline.
The model and public-page results in these tests are fixtures, not live local-model completions.

The Windows installer retains the hash check, source tests, native compile, native protocol/workflow
self-tests and an actual owned-worker rejection check before host replacement. These native gates
cannot be executed in this Linux build environment. The known Windows encoding regression remains
covered. This package is a test candidate, not full research or Bundle B production acceptance.

The next target-PC check is a single comparison using the official
[RobotFileParser documentation](https://docs.python.org/3.12/library/urllib.robotparser.html) and
[urlopen documentation](https://docs.python.org/3.12/library/urllib.request.html). The answer should
separate the parsed-rules decision from opening a URL, use both sources appropriately, avoid
restating the same point, and show useful previews. See [setup](RESEARCH_PREVIEW_SETUP.md).

Real-model wording/relevance, new native installation, live research Stop/exit, rollback, repeated-run
latency/VRAM behavior, stronger OS containment and automatic search remain unverified or deferred.
Keep the working 9.0.1 folder for reinstall rollback. No old Notepad/Calculator test marathon is needed.
