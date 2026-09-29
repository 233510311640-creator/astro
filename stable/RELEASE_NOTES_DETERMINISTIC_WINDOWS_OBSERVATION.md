# Cypher v0.8.4 Deterministic Windows Observation Preview 2

## Preview 2 installer correction

Preview 1 contained a truncated PowerShell installer and therefore stopped at the parser before making any installation change. Preview 2 restores the complete transactional install, heartbeat verification, rollback fallback, and temporary-build cleanup sections.

The launcher now asks Windows' own PowerShell parser to validate the complete installer before executing it. A parser error exits immediately and makes no installation change.

## Outcome

This build fixes the repeated `windows_list_apps` failure without granting Cypher broader authority. Unambiguous read-only Windows observation now runs inside the compiled resident host before Hermes or model routing.

## Direct requests

- `List my registered Windows applications. Do not launch anything.`
- `Show my visible desktop windows. Do not change anything.`
- `Which window is active? Do not change focus.`
- `Show Windows observation status.`

The first three produce bounded local metadata. The fourth explains the boundary. The UI labels this path **DIRECT · WINDOWS OBSERVATION**.

## Not added

- no application launch or focus change on the direct path;
- no clicks, typing, screenshot, shell, PowerShell, or arbitrary command;
- no new folder or file authority;
- no Hermes, Ollama, model, MCP-root, or approval configuration change;
- no prompt or response content in persistent logs.

## Upgrade

1. Extract the complete ZIP into a fresh folder.
2. Finish or stop any active Cypher task.
3. Double-click `INSTALL_CYPHER_DETERMINISTIC_WINDOWS_OBSERVATION.cmd` from a normal, non-administrator Windows account. Its first action is a syntax-only PowerShell parser preflight.
4. Wait for tests, compilation, executable self-test, and loopback Hermes capability checks.
5. Press `Ctrl+Alt+Space` and run the three read-only acceptance prompts above.

The existing Hermes MCP registration and permissioned operator remain in place. Do not rerun the failed v0.8.3 local-runtime repair.
