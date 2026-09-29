# Validation — bounded public site search

The complete suite ran 580 tests: 579 passed and one existing platform check skipped.
The installer passed its parser, all required test groups, native compilation and
self-test, WPF layout, four owned-worker self-tests and transactional replacement.
The installed host is READY on `0.7.0-core-preview10.8.0`, with its research-worker
hash matching the release source. Focused fixtures cover bounded parsing, exact GET request
construction, duplicate identical forms, hidden/POST/off-site/ambiguous rejection,
no model call and cross-host redirect blocking.

A live installed-worker check on the public Python documentation home page completed with
two pages read and four exact fetched-page excerpts for `asyncio`. The page uses three
identical search boxes, which resolve to one request. Wikipedia and DuckDuckGo homepage
forms rejected without sending a query; Project Gutenberg's eligible search action was
blocked by robots policy before a result-page fetch. Static excerpts do not prove that
JavaScript-populated result entries were displayed.
