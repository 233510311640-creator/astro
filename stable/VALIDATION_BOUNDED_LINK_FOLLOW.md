# Validation — bounded link follow

26 September 2026. The complete Python suite ran 571 tests: 570 passed and one existing
platform-specific check skipped. It covers command parsing, exact numbered selection,
fresh-map missing numbers, no model call, and off-host redirect rejection before connect.

The Windows installer passed its PowerShell parser, all required test groups, native host
compilation and self-test, WPF layout checks, owned research/file/runtime/document worker
self-tests, and transactional replacement. The resident host started on
`0.7.0-core-preview10.6.0` and the installed research worker SHA-256 matched the pinned source.

A live installed-worker command, `Web: follow https://en.wikipedia.org/wiki/Chess : 1`, completed:
two pages read, four exact excerpts, one selected same-host destination, no local-model call.
This validates public-page reading; it does not claim browser UI automation or form handling.
