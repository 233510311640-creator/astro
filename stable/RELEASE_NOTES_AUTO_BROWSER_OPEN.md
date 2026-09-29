# Release notes — Cypher 10.2.1 Auto-Discovered Browser Open

This release removes the manual registration step for the four supported browsers: Brave, Microsoft Edge, Google Chrome, and Mozilla Firefox.

- A registered application remains the first choice when an exact registered match exists.
- Otherwise, the requested supported browser is resolved only from fixed Program Files, Program Files (x86), or Local AppData locations.
- Symlink/reparse-point executables are rejected.
- The exact executable path, metadata, SHA-256 hash, browser identity, normalized public HTTPS destination, and 60-second expiry are bound into the one-time approval.
- Execution re-discovers and re-hashes the executable, launches it directly with one HTTPS argument, and never uses the Windows shell or `PATH` lookup.
- Arbitrary applications are not auto-discovered and still require explicit registration.
- Cypher verifies destination delivery to the browser process/window only. It does not claim that the page loaded and does not read or control website content.
