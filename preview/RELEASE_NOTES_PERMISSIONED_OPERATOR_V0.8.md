# Cypher v0.8.0 Permissioned Local Operator — Alpha 1.3 Release Notes

Build date: 2026-08-22  
Status: source candidate; target-Windows acceptance required

## Alpha 1.3 direct-tool reliability hotfix

- Upgrades the resident host to Core Preview 7.1.3.
- Calls exact visible MCP tool schemas directly. Deferred discovery is used only when the exact
  schema is absent, and any returned tool wire name is preserved verbatim.
- Adds an explicitly confirmed and automatically reversible helper that switches Hermes' small
  22-tool catalog from deferred discovery to direct schema loading.
- Adds a strict, content-free terminal-failure receipt and `failure-status` manager action.
- Forbids terminal, shell, ambient file tools or invented commands as substitutes for a requested permissioned MCP workflow.
- Makes no broker, root, permission or model changes when installing or configuring the hotfix.

## Delivered together in this build

- Replaceable fast/deep/vision roles and bounded sequential multi-model workflow policy.
- Human-managed real-folder permission records with separate capability scopes.
- Six new Hermes MCP tools, bringing the broker inventory to 22 narrow tools.
- Bounded UTF-8 text reads from explicit roots.
- Encrypted, fingerprinted plans for create text, replace text, copy file, move file, rename file,
  create directory and reversible quarantine.
- Exact human-side proposal review and time-limited approval.
- Up to 50 actions/2 GB per plan, source snapshots, collision refusal and no-overwrite semantics.
- Per-step protected recovery records, SHA-256 postcondition verification, reverse batch rollback,
  restart reconciliation and human-only undo.
- Windows current-user DPAPI production storage plus an install-time DPAPI round-trip preflight.
- Metadata-only audit behavior that excludes prompts, answers, content, paths and filenames.

## Verification completed here

- Python compilation completed without errors.
- 173 source and regression tests passed.
- The suite covers path traversal, protected names, links/reparse handling, scope denial, plan tamper,
  changed sources, late collisions, approval expiry, batch rollback, partial-copy staging recovery,
  interrupted human undo, audit privacy and MCP authority separation.

## Still required on the target Windows PC

- Run the complete test suite and DPAPI preflight through the included setup script.
- Re-register `hermes-sandbox` and confirm exactly 22 tools.
- Use only a disposable test root for the first acceptance run.
- Test all action types, Stop/restart recovery and protected undo.
- Run `CONFIGURE_CYPHER_HERMES_TOOLS.cmd`, confirm the direct tool mode, and verify the registered
  server still exposes exactly 22 tools.
- Confirm the installed Preview 7.1.3 resident shell calls the operator tools, streams, cancels and starts normally.

This release does not yet wire operator approval/status cards into the Cypher WPF command center.
During Alpha 1, real-folder permission, approval and undo remain deliberate human-side PowerShell
steps. The next development task after target acceptance is that UI/backend lifecycle integration,
followed by the read-only Windows and research operator bundle.
