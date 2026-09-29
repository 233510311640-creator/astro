# Cypher v0.8.3 Local Runtime Repair 7

This narrowly repairs the local Hermes/Ollama failure in which a fresh Cypher request is replaced by text about a previous or truncated response before any tool starts.

## What it changes

- Sets Hermes `model.max_tokens` to `16384`.
- Sets Hermes `model.context_length` and `model.ollama_num_ctx` to `65536`.
- Enables Hermes's bounded MCP discovery bridge with `tools.tool_search.enabled=on`.
- Forces the bounded tool-name listing on so the local model can copy exact MCP wire names.
- Restarts only the local Hermes gateway and, if it was already running, Cypher.
- Saves the five previous setting values for an exact rollback.

It does not update Hermes, install or remove Ollama models, delete cache files, request administrator rights, widen any broker root, or enable unrestricted terminal/file tools.

## Run

1. Extract the entire ZIP into its own folder.
2. Finish or stop any active Cypher task.
3. Double-click `REPAIR_CYPHER_LOCAL_RUNTIME.cmd`.
4. Type or paste `REPAIR CYPHER LOCAL RUNTIME`.
5. Wait for every `[PASS]` preflight line and the final verified-success message.

The repair first runs a 45-second-bounded MCP registration probe and confirms that the broker advertises `windows_list_apps`. It then refuses to claim success unless a fresh Hermes run uses only the discovery bridge plus `windows_list_apps`, completes that read-only tool, and returns without false continuation/truncation language. The application inventory, prompt, response, credentials, and raw event stream are not saved or printed.

Repair 7 corrects the actual tool-loading fault. A [current upstream Hermes issue](https://github.com/NousResearch/hermes-agent/issues/73739) documents that `tools.tool_search.enabled=off` can leave MCP tools connected but absent from the API agent. The repair follows Hermes's [Tool Search guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/tool-search.md): it enables the supported discovery bridge, keeps an exact tool-name listing visible, and recognizes only `tool_search`, `tool_describe`, `tool_call`, and the intended read-only `windows_list_apps` capability during verification. No launch, focus, terminal, or file-write tool is accepted.

If the live preflight fails, the helper automatically restores the settings captured immediately before that attempt and restarts the local gateway. Send the visible error for the next diagnosis.

After success, open Cypher with `Ctrl+Alt+Space` and retry:

> List my registered Windows applications. Do not launch anything.

## Other commands

- `TEST_CYPHER_LOCAL_RUNTIME.cmd` repeats the live no-launch preflight without changing settings.
- `ROLLBACK_CYPHER_LOCAL_RUNTIME.cmd` restores the saved pre-repair Hermes values.
- To view status without running a model, run in PowerShell:

  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\manage_cypher_local_runtime_windows.ps1 status`

## Why this repair exists

Hermes can treat a locally truncated or incompletely terminated model stream as an interrupted previous response. Explicit response and context limits prevent the local Ollama path from repeatedly ending in that ambiguous state. The current Hermes eager-loading regression can independently hide otherwise healthy MCP tools when tool search is off; Repair 7 uses the bounded bridge and verifies both registration and a real tool call instead of assuming either layer works.
