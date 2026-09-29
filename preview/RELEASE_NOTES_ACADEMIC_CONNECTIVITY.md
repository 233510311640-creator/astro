# Core Preview 9.2.1 — OpenAlex connectivity reliability

Package **v0.9.2.1** · Python package **0.9.2a2** · 1 September 2026

## Why this correction exists

The target-PC 9.2.0 acceptance request entered the intended academic route but finished with the
generic `PAPERS_UNAVAILABLE` diagnostic before reading a source. The exact OpenAlex query and response
schema were independently validated. Version 9.2.1 corrects the remaining transport ambiguity and
reports remote status classes precisely.

## Changed

- All IPv4 answers from one DNS result must still pass the public-address policy.
- Cypher may try at most four members of that validated set while establishing TCP/TLS, before the
  single HTTP request is sent. Those attempts share one existing bounded connection window.
- The first successful address is pinned for the request and TLS continues to validate
  `api.openalex.org`.
- A certificate-verification failure stops immediately. It never falls through to another address.
- Once the HTTP request begins, no connection or HTTP retry occurs.
- Anonymous rate limiting, access denial, provider 5xx failure, pre-request connection exhaustion,
  interrupted exchange, and other unsuccessful statuses now have distinct fail-closed diagnostics.

## Unchanged boundaries

There is still one keyless OpenAlex Works request, at most three returned records, at most two
reconstructed abstracts, and one installed-local-model synthesis. No API key, billing credential,
provider fallback, pagination, PDF/full-text read, browser session, model download, action tool,
approval card, or arming countdown was added. Stop appears only while the owned research worker runs.

The accepted Wikipedia, explicit-URL, desktop-isolation, and Windows-workflow code is unchanged.

The focused research suite passes 155 tests. The complete suite discovers 378 tests: 377 pass and
the expected native Windows compiler test is skipped in the Linux packaging environment.

## Acceptance

Install from a new extracted folder and run the single prompt in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md). A completed cited report accepts this focused
fix. If it fails, capture the new exact `PAPERS_...` diagnostic; do not add credentials or broaden
permissions.
