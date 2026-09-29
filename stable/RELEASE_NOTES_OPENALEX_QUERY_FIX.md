# Core Preview 9.2.3 — OpenAlex natural-question fix

> Historical notes for accepted 9.2.3 transport behavior. Its target-PC request completed, but the
> result exposed indirect relationship evidence. The current candidate is 9.2.4; use
> [current setup](RESEARCH_PREVIEW_SETUP.md) and
> [current release notes](RELEASE_NOTES_DIRECT_EVIDENCE_RELEVANCE.md).

Package **v0.9.2.3** · Python package **0.9.2a4** · 2 September 2026

## Why this release exists

The target-PC status check proved that Cypher reached OpenAlex successfully but received HTTP 400.
OpenAlex reported that the ordinary final `?` in the typed research question was being interpreted as
wildcard syntax, which requires a different exact-search parameter. The installation, DNS selection,
TLS connection, request count, local model, and user workflow were not at fault.

## Exact correction

Cypher now retains two bounded values for an academic request:

- the original cleaned question, unchanged and used for the one local-model synthesis; and
- a transport-only provider query in which ASCII `?` and `*` are converted to spaces and whitespace
  is collapsed.

No other character is rewritten. A query containing only those reserved characters and whitespace
fails before any network request. The provider query continues to use OpenAlex's ordinary stemmed
search rather than `search.exact`, because the user asked a natural-language question and did not
request wildcard or literal no-stem semantics.

OpenAlex receives the punctuation-safe terms first. If—and only if—OpenAlex returns exactly HTTP
503, Crossref receives the same normalized terms in the existing one-request fallback. The original
question remains local in both cases.

## Fail-closed behavior

An OpenAlex HTTP 400 now reports `PAPERS_REQUEST_REJECTED`. It does not retry, wait, use Crossref,
request a key, or alter the query a second time. The existing exact-503 transition is unchanged:

| OpenAlex outcome | Cypher behavior |
|---|---|
| HTTP 200 | Validate OpenAlex records; never contact Crossref. |
| HTTP 400 | Report `PAPERS_REQUEST_REJECTED`; never contact Crossref. |
| HTTP 503 | Contact Crossref exactly once with the same normalized terms. |
| Any other outcome | Retain its existing fail-closed diagnostic; never contact Crossref. |

## Unchanged boundaries

- no account, API key, authorization header, billing credential, or payment;
- no retry, `Retry-After` wait, provider loop, extra warning, approval, or arming countdown;
- one installed local-model synthesis call at most;
- at most two checked abstract sources from at most three provider-ranked records;
- no paper page, PDF, full-text fetch, browser login, scripts, or action tools;
- existing owned-worker Stop behavior, Windows desktop restrictions, and metadata-only persistence;
- accepted Wikipedia, explicit-URL, registered-app, and Windows workflow behavior.

## Verification scope

The focused research suite now includes natural terminal punctuation, embedded `*`, preservation of
the original local-model question, identical normalized terms across the exact-503 fallback, and
wildcard-only rejection before network access. All 167 focused research tests pass. The complete
suite discovers 390 tests: 389 pass and the one native Windows compiler test is expectedly skipped
in the Linux build environment. EncodingWarning-as-error and bytecode compilation checks also pass.

The single target-PC acceptance request is documented in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md). No status checker, Stop test, approval test,
or Windows workflow retest is required.

## Provider references

- [OpenAlex search](https://help.openalex.org/api/searching/)
- [OpenAlex API errors](https://help.openalex.org/api/errors/)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
