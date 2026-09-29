# Cypher v0.8.5.1 Deterministic Windows Control Routing Fix

## Outcome

This build adds the first deterministic, approval-gated Windows actions to the compiled Cypher resident host. Exact app launch and exact window focus no longer depend on a local model deciding to discover or call a Hermes tool.

## Routing fix

- Accepts `Focus window 123`, `Focus window ID 123`, and `Focus the window with ID: 123`.
- A focus-shaped request with a missing, placeholder, stale, or row-number ID is rejected locally with corrective guidance.
- Invalid focus targets cannot fall through to Hermes, cannot start a model run, and cannot produce the misleading before-tool failure screen.

## Added

- `Launch <registered app>` resolves only a human-registered app ID or display name and supplies no arguments.
- `Focus window <numeric ID>` resolves only an exact currently visible titled window returned by Cypher's observation route.
- A native **Approve once / Deny** card displays the exact target evidence before any action.
- Each approval is memory-only, SHA-256 fingerprinted, expires after 60 seconds, is consumed before execution, and cannot be replayed.
- App launch revalidates the registry record, executable metadata and full SHA-256 before calling the exact executable.
- Window focus revalidates the handle, title, class and PID before requesting the foreground change.
- Cypher checks a local postcondition and refuses to claim success when it cannot verify the requested result.
- The installer now runs the Windows-operator behavioral tests in addition to the resident-host and broker regression suites.

## Not added

- no arbitrary executable paths, app arguments, shell, PowerShell, or command execution;
- no typing, clicking, screenshots, process termination, or unrestricted UI automation;
- no permanent approval, unattended execution, administrator rights, or startup action replay;
- no change to Hermes, Ollama models, MCP roots, app registrations, file permissions, or privacy logging.

## Install

1. Extract the ZIP into a fresh folder.
2. Finish or stop any active Cypher task.
3. Double-click `INSTALL_CYPHER_WINDOWS_FOCUS_ROUTING_FIX.cmd` from a normal non-administrator account.
4. Wait for parser preflight, tests, compilation, self-test, Hermes capability checks, startup switch and heartbeat verification.
5. Press `Ctrl+Alt+Space` and follow the launch/focus acceptance sequence in `CYPHER_CORE_PREVIEW_README.md`.

The installer preserves the verified v0.6.3 shortcut for cooperative rollback and refuses to replace a host reporting active work.
