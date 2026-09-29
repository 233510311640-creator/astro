# Validation — bounded public form inspection

Source suite: 575 tests, 574 passed and one existing platform-specific skip. New fixtures
check strict command parsing, same-host actions, form and field bounds, non-display of
input/hidden/password values, no model call, and no submission or destination request.

The installer passed its PowerShell parser, all required test groups, native compilation
and compiled self-test, WPF layout, four owned-worker self-tests, and transactional
replacement. The installed host reports READY on `0.7.0-core-preview10.7.0` and its
research-worker hash matches the pinned release source.

A live installed-worker request to inspect the public English Wikipedia Main Page
completed with one page read and two form structures returned. No form was submitted.
