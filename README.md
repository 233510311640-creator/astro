# Cypher — local Windows assistant

For the current feature list, verification results, and remaining work, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

This repository contains the current Cypher project in two self-contained bundles:

- [`stable/`](stable/) — Core Preview 10.20.3, the version currently installed and running on the development PC. `Ctrl+Alt+Space` starts a voice command; holding `Ctrl+Win+Alt` opens the chat.
- [`preview/`](preview/) — Core Preview 10.21.0, an experimental hands-free voice update. Its automated checks pass, but the supervised wake-word acceptance test has **not** passed. Do not replace the stable installation with it yet.

Start with each bundle's `README.md` and release notes. On Windows, the stable installer is `stable/INSTALL_CYPHER_CORE_PREVIEW.cmd`; it runs local validation before installing. The preview installer should be used with `-ValidationOnly` until its live-microphone gate passes.

The repository contains source code, tests, documentation, required packaged workers, and UI assets. It does not contain API credentials, local runtime models, microphone recordings, user files, the installed application's data, or the older duplicate release snapshots.

Cypher's Windows/file actions retain their approval boundaries. Review the relevant `SECURITY_*.md` documents before enabling or extending capabilities.
