# Core Preview 9.2.2 — bounded Crossref fallback

> Historical notes for 9.2.2. Its exact-503 fallback is retained, but a subsequent target-PC request
> exposed an OpenAlex HTTP 400 conflict with ordinary question punctuation. The current candidate is
> 9.2.4; use [current setup](RESEARCH_PREVIEW_SETUP.md) and
> [current release notes](RELEASE_NOTES_DIRECT_EVIDENCE_RELEVANCE.md).

Package **v0.9.2.2** · Python package **0.9.2a3** · 2 September 2026

## Why this release exists

The target PC proved that OpenAlex transport, DNS selection, TLS, and the single request all worked,
but OpenAlex returned HTTP 503 with `Retry-After: 60` because anonymous search was temporarily paused
under load. Waiting and retrying would slow the fast path and create another uncertain stage. Adding
an account or API key was also unnecessary for this local preview.

This release implements the selected option: OpenAlex stays primary, and only its exact HTTP 503
permits one immediate keyless Crossref Works request with the same bounded question.

## Exact transition rule

| OpenAlex outcome | Cypher behavior |
|---|---|
| HTTP 200 | Validate OpenAlex records; never contact Crossref. |
| HTTP 503 | Contact Crossref exactly once, immediately. |
| Any other HTTP status | Fail closed with the OpenAlex diagnostic; never contact Crossref. |
| Invalid/truncated OpenAlex response | Fail closed; never contact Crossref. |
| Connection or post-send network failure | Fail closed; never contact Crossref. |

The two possible provider requests are not retries of each other. There is no repeated attempt,
backoff, `Retry-After` wait, provider loop, API key, account, billing credential, payment, extra
approval, warning, or arming countdown.

## Crossref evidence boundary

The fallback query requests no more than three journal-article records that report deposited
abstracts. Only DOI, title, abstract, type, and language fields are selected. Responses are bounded
and duplicate-key checked. Every accepted record requires a canonical DOI, bounded clean title,
journal-article type, valid optional language and score types, and a bounded abstract.

Publisher-deposited JATS/HTML-like abstract markup is parsed as untrusted data. Script, style, object,
embed, iframe, SVG, canvas, and template contents are discarded. The remaining text is normalized,
bounded, conservatively screened for English when no explicit language is present, and split into
the same reader-assigned evidence passages used by the OpenAlex route.

Crossref titles, DOI values, ranking, scores, and other metadata are excluded from the local-model
evidence payload. Source links use canonical `https://doi.org/...` URLs. The report hashes the exact
normalized deposited abstract text and discloses that Crossref metadata does not independently
guarantee language or retraction status.

## Unchanged boundaries

- one installed local-model synthesis call at most;
- at most two abstract sources;
- no paper page, PDF, or full-text request;
- no action tools or transfer into action-capable Hermes history;
- metadata-only resident logging;
- existing owned-worker Stop and fail-closed Windows job UI restrictions;
- accepted Wikipedia, explicit-URL, Windows workflow, and approval behavior.

## Verification scope

Automated cases cover exact 503-only routing, request order, same-question transfer, no credential
parameters, non-503 refusal, no retry, Crossref status/error mapping, strict JSON/record/DOI/language/
score validation, deposited-markup normalization, active-content exclusion, duplicate suppression,
adaptive third-record use, metadata exclusion from the model payload, provider/source mismatch
rejection, report disclosure, citations, and retained Windows worker isolation.

All 166 focused research tests pass. The complete suite discovers 389 tests: 388 pass and the one
native Windows compiler test is expectedly skipped in the Linux build environment.

The one target-PC acceptance request is documented in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md). No Stop or workflow retest is required.

## Provider references

- [OpenAlex API authentication](https://help.openalex.org/api/authentication/)
- [OpenAlex API errors](https://help.openalex.org/api/errors/)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [Crossref REST API filters](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)
