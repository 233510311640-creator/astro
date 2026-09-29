> Historical notes for the accepted 9.1.1 baseline. The current candidate is 9.2.4; use
> [current setup](RESEARCH_PREVIEW_SETUP.md) and
> [current release notes](RELEASE_NOTES_DIRECT_EVIDENCE_RELEVANCE.md).

# Core Preview 9.1.1 — bounded Wikipedia reader reliability

Package **v0.9.1.1** · Python package **0.9.1a2** · 1 September 2026

## Outcome

The accepted 9.1.0 live run read two Wikipedia sources and produced four cited findings, then tried a
third candidate that was discarded as `CONTENT_LIMIT`. Preview 9.1.1 makes that path more efficient
and more useful without widening research authority.

Question-only discovery now preserves the provider's relevance order and stops after two usable
sources. A readable page larger than 1 MiB contributes only a disclosed bounded prefix instead of
being discarded. The same installed local model still receives one synthesis request.

## Relevance-ordered two-source target

- The one official MediaWiki search request explicitly asks for relevance order and still accepts at
  most three namespace-0 title/page-ID records.
- Candidate URLs are attempted serially in that returned order.
- Cypher stops once two sources have passed URL, DNS, TLS, robots, redirect, content-type, extraction
  and duplicate checks.
- If an earlier candidate fails or duplicates an accepted final URL, the next candidate can fill the
  two-source target.
- Lower-ranked candidates are not fetched after the target is met, and the report discloses how many
  were skipped.
- Explicit one-to-five-URL research remains separate and attempts every selected source.

This rule adds no provider request, pagination, fallback, retry or relevance judgment of Cypher's
own. Search titles and metadata remain candidate locators, never evidence.

## Bounded page prefixes

- A successful uncompressed HTML/XHTML/plain-text response retains no more than 1 MiB.
- If `Content-Length` already proves the body is larger, Cypher reads only the 1 MiB prefix.
- Without a usable announced length, Cypher reads at most one additional byte to detect overflow,
  then discards that detection byte and closes the response.
- Extraction, passage construction, local synthesis and citation checks use only the retained prefix.
- The report says when the response exceeded 1 MiB and hashes only the bytes actually retained.
- Truncated discovery JSON remains invalid. Truncated robots policy remains unavailable and cannot
  authorize a page read.

Invalid or negative size metadata still fails closed. This behavior does not convert compressed,
authenticated, scripted, PDF or unsupported content into evidence.

## Latency, privacy and authority

The change removes unnecessary candidate reads when two sources are already usable. It adds no
approval card, countdown, arming delay, warning step, model generation or special Stop interaction.
The existing Stop button owns the same worker. Consequential Windows actions retain their existing
fresh one-time approval.

Only the typed research question and ordinary network metadata leave for the one discovery request.
Candidate page requests disclose their URLs and ordinary network metadata. No chat history, local
file, durable memory, application state, model prompt or answer is forwarded. Research still has no
action, file, shell, browser-login or Hermes tool authority.

## Retained boundaries

- one fixed English Wikipedia Action API request for question-only discovery;
- strict 64 KiB discovery JSON and validated title-only URL construction;
- public-address and pinned-TLS checks, robots policy, redirect bounds and content-type checks;
- one installed local-model generation with no tools, download, substitution or cloud fallback;
- reader-assigned passage IDs, exact excerpts, citation validation and the scope/vocabulary guard;
- memory-only reports outside Hermes chat/action history;
- accepted Windows job desktop restrictions; and
- byte-identical accepted Windows workflow sources.

The worker remains standard-user process/job isolation, not AppContainer filesystem, registry or
network containment.

## Verification

The focused research suite passes 139 tests. New coverage proves:

- explicit `srsort=relevance` construction;
- two successful discovered pages prevent a third page request;
- a failed first candidate permits the third candidate to fill the target;
- explicit source requests still attempt all selected URLs;
- known-length and unknown-length oversized responses retain exactly the bounded prefix;
- ordinary exact-limit responses are not marked truncated;
- readable page prefixes become evidence rather than `CONTENT_LIMIT` failures;
- truncated discovery JSON is rejected; and
- truncated robots responses never become permission.

The complete suite discovers 362 tests: 361 pass and one expected Windows-only compiler test is
skipped on Linux. CP1252-default and EncodingWarning-as-error checks pass. The installer still
compiles and self-tests the native host before replacement.

## Focused target-PC gate

Install from a new extracted folder with accepted 9.1.0 retained for rollback. Repeat only:

```text
Research: What is robots.txt and what does it control?
```

The result should identify provider relevance order and list at least one read Wikipedia source. If
the first two candidates are usable, it should say that one lower-ranked candidate was not fetched.
If an attempted page exceeds the cap, it should disclose the bounded prefix rather than discard that
source solely for size. No workflow, approval, Stop-race, explicit-source or model-installation
retest is required.

## Official provider reference

- [MediaWiki Action API search](https://www.mediawiki.org/wiki/API:Search)
