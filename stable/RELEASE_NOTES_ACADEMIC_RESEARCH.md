> Historical notes for the 9.2.0 academic-route introduction. The target-PC request reached the
> route but returned `PAPERS_UNAVAILABLE`; the current candidate is 9.2.4. Use
> [current setup](RESEARCH_PREVIEW_SETUP.md) and
> [current release notes](RELEASE_NOTES_DIRECT_EVIDENCE_RELEVANCE.md).

# Core Preview 9.2.0 — bounded academic research

Package **v0.9.2.0** · Python package **0.9.2a1** · 1 September 2026

## Added

- A separate `Research papers: QUESTION` route before ordinary chat routing.
- One fixed, keyless official OpenAlex Works API request per accepted paper request.
- Strict selection of at most three English, non-retracted records with abstracts.
- Deterministic reconstruction and validation of OpenAlex's inverted abstract representation.
- At most two provider-ordered abstracts in one existing-local-model synthesis call.
- Public OpenAlex work links, exact abstract-passage citations, retrieval time, and SHA-256 of the
  reconstructed abstract text.

## Evidence boundary

Only reconstructed abstract text can enter the model evidence catalog. Provider titles are retained
for final source display, while titles, Work IDs, ranking, relevance score, citation counts,
publication metadata, and response metadata are excluded from model input. The existing passage-ID,
source/offset, exact quotation, duplicate-key, output-schema, and claim-scope checks apply before any
finding is shown.

Malformed, oversized, truncated, non-JSON, duplicate-field, over-count, unexpected-schema,
non-English, retracted, invalid-ID, or non-contiguous abstract data fails closed. Network failure,
rate limiting, or provider rejection triggers no retry, alternate provider, or automatic replay.

## Privacy and cost boundary

The request sends the typed paper question and ordinary public network metadata to OpenAlex. It sends
no chat history, file, memory, app state, local-model prompt/answer, API key, authorization header, or
billing credential. The route does not download a model, PDF, full text, attachment, or report.

OpenAlex operates its own service policy and may rate-limit or change the endpoint. Cypher performs
only the keyless call and has no configured paid-account or billing path.

## Interaction

There is no new approval, warning countdown, arming state, or preflight click. Send starts the bounded
request immediately. The existing Stop control remains available while the owned worker is active.

## Retained and deferred

The accepted 9.1.1 Wikipedia and explicit-source routes, Windows worker desktop restrictions, local
models, and approved Windows workflows remain. General-web/current-news discovery, provider
connectors, PDF/full-text retrieval, AppContainer-style filesystem/network containment, memory,
voice, and vision input remain future milestones.

## Verification

The focused research suite passes 151 tests. The complete suite discovers 374 tests: 373 pass, and
the expected native Windows compiler test is skipped in the Linux build environment. The
EncodingWarning-as-error research run and Python bytecode compilation pass. Installation still runs
the required source suites and native Windows compilation/self-tests before replacing the resident host.
The remaining release gate is the single live target-PC paper request in the setup guide.

Use [RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md) for installation and the one target-PC
acceptance request.
