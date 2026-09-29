# Cypher v0.8 Permissioned Local Operator — Alpha 1.3

> This document describes the earlier v0.8.0 operator milestone. For the current combined file and
> Windows-application build, use `WINDOWS_OPERATOR_PREVIEW_SETUP.md`.

This release adds supervised real-folder work to the existing Cypher/Hermes capability broker. It
does not grant Cypher access to the whole user profile. A person must add every folder and select
its exact capabilities before Hermes can even propose an action.

## What Alpha 1 can do

- read bounded UTF-8 text from explicitly approved roots;
- create or replace small approved text files;
- copy, move or rename bounded files without overwrite;
- create one directory;
- move a file into protected Cypher quarantine instead of permanently deleting it;
- combine up to 50 actions and 2 GB into one fingerprinted plan;
- execute only after a separate human approval of that exact fingerprint;
- verify every postcondition, roll back a failed batch, reconcile an interrupted operation after a
  restart, and provide human-side undo.

Operator plan and undo payloads are protected with Windows current-user DPAPI. Metadata-only audit
events do not include prompts, responses, file contents, requested paths or filenames.

## Install beside the existing versions

1. Extract the ZIP into a new stable folder, for example:
   `%USERPROFILE%\Desktop\cypher-v0.8.0-permissioned-operator-alpha1.3`
2. Open PowerShell in that extracted folder.
3. Run:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\scripts\setup_capability_broker_windows.ps1
   ```

4. The setup runs the complete local test suite and creates `REGISTER_COMMAND.txt`. It does not edit
   Hermes, approve any real folder or move any file.
5. Remove the older registration and add this version using the generated command:

   ```powershell
   hermes mcp remove hermes-sandbox
   notepad .\REGISTER_COMMAND.txt
   ```

   Confirm the removal, copy the single command from Notepad, run it, and answer `y` when Hermes asks
   whether to enable all 22 tools.
6. Restore the conservative MCP switches and test the connection:

   ```powershell
   hermes config set mcp_servers.hermes-sandbox.supports_parallel_tool_calls false
   hermes config set mcp_servers.hermes-sandbox.sampling.enabled false
   hermes config set mcp_servers.hermes-sandbox.elicitation.enabled false
   hermes mcp test hermes-sandbox
   ```

Do not continue if the setup tests fail or Hermes discovers a different tool count.

## Configure reliable bounded tool discovery

After the 22-tool MCP test passes and no Cypher task is active, double-click
`CONFIGURE_CYPHER_HERMES_TOOLS.cmd`. Type `CONFIGURE BOUNDED CYPHER TOOLS` only after reviewing its
summary. The helper changes only Hermes' tool-search and exact-name listing modes, restarts the loopback gateway and
retests `hermes-sandbox`; it restores both former settings if that test fails. It does not add a root,
permission, model, approval or built-in tool.

## Add a real-folder permission

Create a dedicated test folder first. Do not begin with Desktop, Documents, Downloads, a cloud-sync
root or an irreplaceable folder.

```powershell
$operator = ".\scripts\manage_permissioned_operator_windows.ps1"
& $operator permissions-add operator-test "$env:USERPROFILE\Desktop\Cypher Operator Test" "read_text,create_text,replace_text,copy,move,rename,mkdir,quarantine"
```

Review the displayed path and capabilities, then type `ADD operator-test`. Restart Hermes or reload
its MCP servers. The model cannot run this command or add a permission itself.

List or revoke permissions with:

```powershell
& $operator permissions-list
& $operator permissions-remove operator-test
```

## Supervised acceptance test

Ask Cypher:

```text
Use only the permissioned operator tools. Show operator permission status. Then propose, but do not
apply, a plan that creates operator-check.txt in root operator-test containing exactly:
Cypher v0.8 operator check passed.
Return the plan ID and approval code.
```

In PowerShell, inspect and approve the exact proposal:

```powershell
& $operator plan-show PLAN_ID
& $operator plan-approve PLAN_ID
```

Type the displayed eight-character approval code only if every action is correct. Then ask Cypher to
apply that same plan ID. Verify the file yourself and ask Cypher for its operation status.

To undo, use the human-only manager:

```powershell
& $operator operation-undo OPERATION_ID
```

Type `UNDO OPERATION_ID`. Undo refuses to overwrite a file that changed after Cypher created or moved
it.

## Important boundaries

- No shell, PowerShell, arbitrary code, administrator access or permanent deletion is added.
- No ambient whole-PC or whole-profile access exists.
- Permissions are per folder and per capability; `metadata` is always present.
- The model may propose and apply an externally approved plan. It cannot add permissions, approve a
  plan, revoke permissions or invoke undo.
- Existing files are never overwritten by create, copy, move or rename.
- Text create/replace is limited to approved plain-text extensions and 65,536 UTF-8 bytes.
- A source file is limited to 512 MB; a plan is limited to 50 actions and 2 GB.
- Review expires after 60 minutes and approved execution expires after 10 minutes.
- Directory trees, arbitrary binaries, application control, browser automation, schedules and
  permanent deletion are not part of this alpha.

See `SECURITY_PERMISSIONED_OPERATOR_V0.8.md` before using personal folders.
