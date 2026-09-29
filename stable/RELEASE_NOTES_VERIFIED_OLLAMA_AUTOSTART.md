# Core Preview 9.2.6 — verified Ollama autostart

Package **v0.9.2.6** · Python package **0.9.2a7** · 4 September 2026

## Confirmed cause

Core Preview 9.2.4 and 9.2.5 both completed OpenAlex discovery and local source selection, then
returned `MODEL_UNAVAILABLE`. The non-installing target-PC checker reported
`RESULT=OLLAMA_NOT_RUNNING`. The academic worker was correctly calling the fixed loopback endpoint,
but the newer compiled host had not retained the older resident launcher's Ollama-start step.

## Change

During installation, Cypher resolves the existing local `ollama.exe` as the signed-in standard
user, rejects a reparse-point executable, and stores its absolute path and SHA-256 in the host
configuration. At each host start:

1. A bounded request checks `http://127.0.0.1:11434/api/version` with redirects and proxies disabled.
2. A valid already-running Ollama is accepted immediately.
3. Otherwise, Cypher rechecks the stored path, reparse-point state, and exact SHA-256.
4. Only that executable may start, with the literal argument `serve`, no shell, no elevation, and
   `OLLAMA_HOST` forced to `127.0.0.1:11434` for that child process.
5. Cypher accepts readiness only after a valid bounded version response, for at most 25 seconds.

Missing, unreadable, changed, non-starting, or non-responsive executables fail closed with a bounded
`OLLAMA_*` diagnostic. The host never searches PATH at runtime.

No model is downloaded, substituted, or retried. The 9.2.5 token-budget experiment is removed;
9.2.4's 16,384-token context and 2,048-token output ceiling are restored. Provider routes,
direct-evidence guard, approvals, Stop behavior, and Windows workflows remain unchanged.

All 172 focused research tests pass. The complete source suite discovers 396 tests: 395 pass and
the one native Windows compiler test is expectedly skipped in the Linux build environment. The
Windows installer compiles the real host and runs its self-test before replacing the active version.
