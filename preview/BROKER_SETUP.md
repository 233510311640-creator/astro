# Hermes Capability Broker v0.5.0

v0.5.0 retains the tested sandbox actions and metadata inventory, then adds persistent **dry-run-only** organization planning for graphic files. It cannot execute a real-folder plan.

The broker must expose exactly sixteen tools: eight sandbox tools, four inventory tools, and four organization-planning tools. Keep every unrestricted Hermes built-in tool disabled.

## 1. Install in a new folder

1. Exit Hermes.
2. Extract the ZIP into a new stable folder such as `%USERPROFILE%\Desktop\hermes-capability-broker-v0.5.0`. Do not overwrite or merge it with v0.4.0.
3. Open normal, non-administrator PowerShell in the new folder.
4. Run:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\scripts\setup_capability_broker_windows.ps1
   ```

Setup runs the packaged tests and writes `REGISTER_COMMAND.txt`. It does not approve a real folder, change Hermes configuration, scan files, or move anything. Your existing v0.4 inventory allowlist remains in `%LOCALAPPDATA%\LocalAssistantBroker\inventory_roots.json`.

## 2. Add a dedicated planning destination

Use a harmless empty test folder first:

```powershell
$planRoot = "$env:USERPROFILE\Desktop\Hermes Organizer Test"
New-Item -ItemType Directory -Path $planRoot -Force | Out-Null
.\scripts\manage_organization_plans_windows.ps1 add-destination organizer-test $planRoot
```

Review the printed boundary and type `ADD-DESTINATION organizer-test`. This permission allows proposed relative paths under the folder only. It does not permit folder creation or file changes.

Inspect or revoke destinations with:

```powershell
.\scripts\manage_organization_plans_windows.ps1 destinations
.\scripts\manage_organization_plans_windows.ps1 remove-destination <DESTINATION-ID>
```

Source roots continue to be managed separately with:

```powershell
.\scripts\manage_inventory_roots_windows.ps1 list
```

The v0.4 acceptance root should still appear as `inventory-test`. Do not approve Desktop, Downloads, or other real working folders yet.

## 3. Replace the registered v0.4 broker

```powershell
hermes mcp remove hermes-sandbox
notepad .\REGISTER_COMMAND.txt
```

Review the command, close Notepad, paste the command into PowerShell, and enable all sixteen tools when prompted. Then run:

```powershell
hermes config set mcp_servers.hermes-sandbox.supports_parallel_tool_calls false
hermes config set mcp_servers.hermes-sandbox.sampling.enabled false
hermes config set mcp_servers.hermes-sandbox.elicitation.enabled false
hermes mcp test hermes-sandbox
```

Stop if the test does not discover exactly **16** tools. Keep all built-in Hermes tools disabled.

## 4. Dry-run acceptance test

Start a fresh Hermes session. Ask:

```text
Use only hermes-sandbox tools. Call organization_status and report the exact safety boundary, approved source roots, planning destinations, and limits. Do not propose or change anything.
```

Confirm:

- `mode` is `dry-run-only`;
- `execution_available` and `real_file_writes` are false;
- `content_reads` is false;
- `local_plan_state_writes` is true;
- source `inventory-test` and destination `organizer-test` are the only test permissions you expected.

Assuming the v0.4 test folder still contains `sample-logo.svg` and `sample-poster.psd`, ask:

```text
Use only hermes-sandbox organization tools. Create one new dry-run graphic organization plan from source root inventory-test to destination root organizer-test. Plan sample-logo.svg to Vectors/sample-logo.svg and sample-poster.psd to Design Sources/sample-poster.psd. Use short plain-text reasons. Do not create folders and do not move, copy, rename, replace, or delete anything. Return the new plan ID, full fingerprint, status, and expiry.
```

Before reviewing, verify in File Explorer that `Hermes Organizer Test` is still empty. Then, in PowerShell from the v0.5 folder:

```powershell
.\scripts\manage_organization_plans_windows.ps1 show <PLAN-ID>
.\scripts\manage_organization_plans_windows.ps1 review <PLAN-ID>
```

Read every source, destination, reason, snapshot, root, fingerprint, and validation result. Type the displayed `REVIEW <8-CHAR-CODE>` only if exact. The command must finish with:

```text
No execution permission was granted. v0.5 cannot move files.
```

Back in a fresh Hermes session, ask it to validate the same plan. The plan may be `reviewed`, but `execution_available` must remain false. Confirm again that the destination folder is empty and both source files remain in place.

To reject a different proposal instead:

```powershell
.\scripts\manage_organization_plans_windows.ps1 reject <PLAN-ID>
```

Review and rejection expire with the 60-minute proposal window. v0.5 has no organization apply command.

## 5. Boundary tests

Ask Hermes to propose `../escape.svg`, rename a source basename, or target an existing destination. Each request must be rejected. Also retain the v0.4 traversal test:

```text
Use only inventory_list_directory with root_id inventory-test and relative_directory .. . Do not find another path. Return the broker's exact result.
```

Stop and remove the integration if traversal succeeds, a real-folder apply/move/copy/delete tool appears, any real file changes during planning or review, the tool count differs from sixteen, or a built-in Hermes tool becomes enabled.

## Local state and privacy

- Inventory roots: `%LOCALAPPDATA%\LocalAssistantBroker\inventory_roots.json`
- Planning destinations: `%LOCALAPPDATA%\LocalAssistantBroker\organization_destinations.json`
- Organization plans: `%LOCALAPPDATA%\LocalAssistantBroker\organization_plan_state.db`
- Sandbox action state: `%LOCALAPPDATA%\LocalAssistantBroker\action_state.db`
- Metadata audit: `%LOCALAPPDATA%\LocalAssistantBroker\audit.jsonl`

The organization database stores plan filenames, proposed paths, model reasons, root paths, metadata snapshots, status, expiry, and fingerprint. Audit events store only plan/root IDs, counts, status, and outcomes—not plan filenames, reasons, or file contents.

## Remove Hermes access

```powershell
hermes mcp remove hermes-sandbox
```

This removes the connection. It does not delete the sandbox, allowlists, destination permissions, state databases, audit, or user files.
