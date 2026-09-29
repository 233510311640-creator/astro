# Cypher v0.8.3 Local Runtime Repair 7

- Fixes the confirmed configuration conflict that left MCP tools connected but absent from Hermes API runs when `tools.tool_search.enabled=off`.
- Enables Hermes's progressive-disclosure bridge and forces its bounded exact-name listing on.
- Adds a 45-second-bounded broker probe that must discover `windows_list_apps`; raw probe output is never printed or persisted.
- Requires a fresh Hermes run to reach and complete the exact read-only capability, while permitting only the three discovery bridge calls as auxiliaries.
- Reports whether the model skipped discovery, chose an unexpected tool, failed to start the intended tool, or failed to complete it.
- Preserves exact rollback of all five modified settings on every failed verification.

- Parses Hermes Runs API lifecycle names from the JSON `event` field used by current unnamed SSE frames.
- Fixes the false zero-tool result that caused Repairs 4 and 5 to reject a correctly started read-only preflight.
- Still requires a completed run, a tool-completion event, the exact success sentinel, and the absence of false continuation text.

- Accepts the exact `windows_list_apps` tool under either its bare broker name or Hermes's canonical `mcp__hermes_sandbox__windows_list_apps` registry name.
- Continues to reject every other MCP server, tool, launch action, focus action, terminal action, and file-write action.
- Preserves the transactional rollback, bounded progress reporting, and fresh-run contamination checks from Repair 4.

- Adds a transactional, standard-user repair for Hermes/Ollama output and context limits.
- Requires live evidence from the exact read-only `windows_list_apps` tool before declaring success.
- Rejects false prior-response, resume, cut-off, or truncation output during verification.
- Preserves and restores all five modified Hermes settings on failed verification.
- Provides a separate no-change preflight and explicit rollback command.
- Does not change Cypher permissions, broker roots, installed models, caches, or Hermes version.
- Corrects Windows PowerShell 5 handling of Hermes's expected `Config key not set` diagnostic.
- Normalizes pasted confirmation text without weakening the explicit phrase gate.
- Returns a distinct cancellation status so a cancelled run cannot be reported as successful.
- Removes the redundant unbounded `hermes mcp test` wait that could freeze after tool discovery.
- Uses the stronger live `windows_list_apps` run as the single MCP verification gate.
- Prints preflight progress every 15 seconds and retains the hard five-minute deadline.
