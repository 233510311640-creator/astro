> Historical notes for accepted 9.1.0 discovery. The current candidate is 9.2.4; use
> [current setup](RESEARCH_PREVIEW_SETUP.md) and
> [current release notes](RELEASE_NOTES_DIRECT_EVIDENCE_RELEVANCE.md).

# Core Preview 9.1.0 — bounded English Wikipedia discovery

Package **v0.9.1.0** · Python package **0.9.1a1** · 1 September 2026

## Outcome

A `Research:` question no longer requires the user to find and paste source URLs. With no URL lines,
Cypher performs one bounded lookup through the official English Wikipedia MediaWiki Action API,
turns up to three validated article titles into candidate URLs, and then uses the accepted page
reader and local evidence pipeline.

This is intentionally a small official-provider slice, not general web search.

## Fixed discovery contract

- Exactly one HTTPS GET to `en.wikipedia.org/w/api.php`.
- Fixed read-only Action API parameters: JSON format, namespace 0, relevance order and at most three
  results.
- The cleaned typed question is the only request value derived from user content and is limited to
  400 UTF-8 bytes.
- Response body is limited to 64 KiB and must be `application/json`.
- Each result must contain a positive integer page ID, namespace 0 and a clean bounded title.
- Cypher constructs the article URL locally on `en.wikipedia.org`.
- Search snippets, provider-supplied URLs, suggestions, scores and all other metadata are ignored.
- Non-200, malformed, oversized, empty or unsafe responses fail closed.
- There is no retry, pagination, alternate provider or HTML search-results scraping.

The MediaWiki documentation identifies `list=search` as its full-text search module. Wikimedia's API
guidelines require labeled user agents and respect for rate limits; Cypher sends a descriptive
name/version agent, uses serial user-initiated requests, and does not retry a throttled response.

## Privacy and authority

Wikimedia receives the typed research question, the PC's public IP/network metadata and Cypher's
name/version user agent. Cypher does not send chat history, local files, durable memory, application
state, prior research, model instructions or generated answers. Users should not place private
information in a discovery question.

Returned titles are candidate locations only. Each article still passes public IPv4 resolution,
pinned TLS, robots policy, redirect, content-type, body-size, extraction and deadline checks.
Fetched page text remains hostile evidence, never instructions or action authority.

Research still has no Hermes/MCP action tools, file tools, application tools, browser login, cookies,
scripts or PDFs. Output remains memory-only and outside the action-capable chat history.

## Latency and user control

Discovery adds one necessary provider request but no extra local-model generation, approval card,
arming delay, countdown or warning step. The existing Stop control owns the same worker and can stop
discovery, page reading or the client side of synthesis. There is no provider fallback or automatic
retry.

## Explicit-source route retained

A `Research:` question followed by one to five public HTTPS URL lines bypasses discovery entirely.
Its question stays local, and its prior request parsing, reader, one-generation synthesis, citations,
scope guard, output and Stop behavior remain.

## Retained isolation

The accepted 9.0.6 Windows job boundary remains: one process, 512 MiB process memory, kill-on-close,
and the complete fail-closed desktop UI restriction mask set and read back before process start.
This is not AppContainer or full filesystem/registry/network sandboxing.

## Verification

The focused tests cover:

- exact provider host/path and query construction;
- one request, 64 KiB response and three-result limits;
- UTF-8 question bounds;
- JSON content type and schema validation;
- title-only URL construction and ignored hostile snippets/provider URLs;
- duplicate, non-article, malformed and oversized results;
- empty, non-200 and network-failure diagnostics with no retry;
- explicit-source requests making no discovery call;
- discovery failure making no page or model call;
- progress order `DISCOVERING → READING → SUMMARIZING`;
- retained worker hash, native host protocol, desktop restrictions and installer gates.

The focused research suite passes 134 tests. The complete suite discovers 357 tests: 356 pass and
one expected Windows-only compiler test is skipped on Linux. The complete suite also passes when
unspecified `Path.read_text()` calls default to CP1252, and the focused suite passes with Python's
default-encoding warnings treated as errors. All four retained Windows workflow source files are
byte-identical to 9.0.6.

Successful installation established the native compiled boundary. The later target-PC question-only
request accepted provider reachability and the installed local-model path with two read sources and
four findings. Its third candidate exposed the `CONTENT_LIMIT` behavior addressed by 9.1.1. Keep
9.1.0 as the immediate rollback package.

## Official provider references

- [MediaWiki Action API search](https://www.mediawiki.org/wiki/API:Search)
- [MediaWiki API etiquette](https://www.mediawiki.org/wiki/API:Etiquette)
- [Wikimedia API usage guidelines](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines)
- [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)
