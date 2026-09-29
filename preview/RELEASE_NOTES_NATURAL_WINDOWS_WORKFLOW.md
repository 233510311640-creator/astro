# Cypher v0.8.8.1 Natural Windows Workflow Preview 1 Fix 1

This release adds Cypher Core Preview 8.4.1 and the first Windows workflow that does not require the user to copy a window ID or UI-control ID.

Fix 1 repairs a target-PC failure found with Windows 11 packaged Notepad. Notepad may refresh its top-level title while the native approval card is visible. The prior build treated that presentation-only change as a replaced window. This build continues to require the exact HWND, PID, window class, registered packaged-app identity, executable metadata/hash, editor identity/path, selection policy, action, text length/hash, and expiry, but no longer mistakes a title refresh for an identity change.

## New workflow

After Notepad is registered and its separate text-entry capability is enabled, ask:

`Open Notepad and write: Cypher natural workflow passed.`

Cypher will:

1. resolve the exact registered application;
2. use exactly one existing matching window, or launch the exact registered executable without arguments when none exists;
3. require exactly one enabled, on-screen, non-sensitive writable editor;
4. display one native **Approve once / Deny** card;
5. revalidate the app, executable, selection policy, window, editor, text hash and expiry; and
6. deliver the exact bounded text through managed Windows UI Automation `ValuePattern.SetValue`.

The approval is consumed before execution, expires after 60 seconds, cannot be replayed, and creates no lasting permission. Multiple matching windows or editors are rejected.

## Validation

- All 212 local source regression tests pass.
- The dedicated launcher performs a complete PowerShell parser preflight before installation.
- The Windows installer must still compile and self-test the resident host on the target PC before switching the active Cypher shortcut.
- This remains a source candidate until the harmless Notepad denial, approval, exact-text, replay and ambiguity checks below pass on the target PC.

## Preserved boundaries

- Local Ollama models and loopback Hermes only.
- Standard-user execution; no administrator or service authority.
- Human-registered applications only.
- Text-entry capability remains separately opt-in per app.
- No raw keyboard/mouse input, SendKeys, clipboard, coordinates, screenshots, shell commands, existing field reads, password controls, or arbitrary action chains.
- Prior v0.6.3 rollback shortcut and the previous v0.8.7.2 release remain untouched.

## Install

Extract the whole ZIP into a new folder and double-click:

`INSTALL_CYPHER_NATURAL_WINDOWS_WORKFLOW.cmd`

The launcher performs a complete PowerShell parser preflight before the installer may change the resident host. The installer then runs the source tests, compiles the host, runs its self-test, verifies Hermes, and switches Cypher only after those checks pass.

## Acceptance test

1. Keep only one blank Notepad window open.
2. Send `Open Notepad and write: Cypher natural workflow passed.`
3. Deny the first approval and confirm nothing changes.
4. Repeat, approve once within 60 seconds, and confirm the exact text appears.
5. Open two matching Notepad windows and repeat; Cypher must reject the ambiguity without acting.

Use only disposable test text and close the test document without saving.
