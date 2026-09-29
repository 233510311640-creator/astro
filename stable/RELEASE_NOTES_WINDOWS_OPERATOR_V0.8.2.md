# Cypher v0.8.2 Windows Operator Preview 2 — Release Notes

## Fixed

- A failed Hermes run can no longer contaminate the next visible user request with stale continuation or output-truncation state.
- Every submitted task now receives a fresh, process-generated Hermes `session_id`.
- Normal conversation continuity is preserved only through Cypher's explicit bounded in-memory history of successful turns.
- The installer no longer persists a reusable Hermes session identifier in `host_config.json`.

## Retained functionality

- 28 broker tools, including registered-app inventory, visible-window observation, foreground-window observation, registered-app launch and verified window-focus requests.
- Standard-user operation, loopback-only Hermes/Ollama connections, bounded approvals and reversible protected file operations.
- Metadata-only checkpoints and content-free failure receipts.

## Verification

- 185 source tests passed.
- The installer rebuilds and self-tests the compiled Windows host before replacing the installed preview.

## Acceptance test

After installation and Hermes tool configuration, open a fresh Cypher window and enter:

> List my registered Windows applications. Do not launch anything.

Expected: Cypher calls the registered-app tool and returns its result. It must not ask what earlier task was interrupted.
