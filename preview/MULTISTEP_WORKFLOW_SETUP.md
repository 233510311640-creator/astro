# Cypher v0.8.9.3 — Hosted Window Fix

Core Preview **8.5.3**. This is a Windows acceptance candidate, not a completed production milestone.

**For this release, start with [Hosted window fix setup](HOSTED_WINDOW_FIX_SETUP.md).** There is no two-second arming pause. The original checks below are reference material; do not repeat the entire already-completed acceptance sequence.

## Install

1. Keep the v0.8.9.2 folder for reinstall rollback. Extract this ZIP into a **new** folder.
2. Finish or deny any active Cypher request. Do not run the installer as administrator.
3. Run **INSTALL_CYPHER_MULTISTEP_WORKFLOW.cmd**.
4. Wait for installation to finish successfully. The installer checks source, compiles and runs
   the workflow behavioral harness, compiles the complete Windows host, and runs its self-test
   before replacing the installed executable.
5. Open Cypher with **Ctrl+Alt+Space**. The heading should say **CORE PREVIEW 8.5.3**.

Do not rerun the brain evaluator, download models, or change app permissions for this upgrade.
The already enabled Notepad text-entry permission is reused. A new app still needs separate human
registration, and writing to it still needs separate text-entry permission.

## First acceptance test

Use one visible **blank, disposable Notepad document**. Close additional Notepad windows and dialogs.
Do not switch tabs or change the target app while approving or executing the plan.

Paste this whole block into Cypher:

```text
Workflow:
Open Notepad and write: Cypher multi-step workflow passed.
Minimize Notepad
```

The preview must show **three actions**:

1. Open or reuse the exact registered Notepad app.
2. Replace the eligible editor's contents with the complete displayed text.
3. Minimize that same bound Notepad window.

First choose **Deny**. No window or document should change.

Submit the same block again, review the full text and targets, and choose **Approve once** within
60 seconds. Expected: Cypher reports **3/3 steps verified**, Notepad is minimized, and restoring it
manually reveals exactly `Cypher multi-step workflow passed.`.

Send the final Cypher result and the visible Notepad text as the Windows acceptance evidence.
A refusal, incomplete scan, compiler error, or unverified step is not a pass.

## Commands

Use one action per line under `Workflow:`. Paste the block, or use **Shift+Enter** for newlines;
plain Enter submits it.

| Action | Meaning |
| --- | --- |
| `Open Notepad` | Reuse its bound window; launch the registered executable without arguments only if absent at preview time. |
| `Write in Notepad: example text` | Replace the contents of the single eligible editor with the literal text. |
| `Open Notepad and write: example text` | Expand into two steps: Open, then Write. |
| `Minimize Notepad` | Minimize the same bound window and check its minimized state. |
| `Restore Notepad` | Restore it if minimized and check that it is no longer minimized. |
| `Focus Notepad` | Restore it if needed, request foreground activation, and check the foreground window. |
| `Show workflow status` | Read counts and state from the last executed workflow; perform no app action. |

`Minimize APP`, `Restore APP`, and `Focus APP` also work as standalone requests.
The earlier `Open Notepad and write: ...` single-command route and exact Window/Control ID commands
remain available.

Limits: **six expanded actions, three registered apps, 500 characters per write, 4,000 characters
per request**. Use the registered display name or its unique registry ID. Arbitrary paths, app
arguments, arbitrary control clicks, closing apps, saving files, and unsupported commands are not
workflow steps. If any line is unsupported, the entire plan is rejected before approval.

Only line boundaries separate instructions. A phrase such as `then minimize Calculator` inside a
write's text stays literal text; it does not become a hidden action.

## Further acceptance checks

- **Natural window actions:** try `Restore Notepad`, then `Focus Notepad`, each with fresh approval.
- **Multiple apps:** add `Open Calculator` after the first test's Minimize line. The existing app
  registry must contain Calculator. The plan should show four steps and two registered apps.
- **No app open:** close disposable Notepad normally, then repeat the first test. Confirm one
  registered Notepad window is opened and receives the approved text. Notepad session restore or
  multiple editors can cause a safe refusal; this path has not been established by the prior screenshot.
- **Stop:** while a plan is running, press Stop. Later steps must not start. The current Windows
  call may finish and receive a receipt; completed changes are not undone.
- **Restart:** after a completed or stopped test, exit Cypher normally and restart it. No prior step
  may run again. A crash/power-loss interruption requires a separate recovery test before stable release.
- **Ambiguity:** with two Notepad windows open, submitting the first test must reject the plan
  before approval. Do not use documents containing valuable unsaved work for these tests.

Windows can refuse a foreground request. That is reported as unverified and stops later steps;
Cypher does not force focus through input injection or an access-control workaround.

## Evidence, privacy, and recovery

Window-state results are checked against fresh registered-app and HWND/PID/class observations.
Writing reuses the existing `ValuePattern.SetValue` implementation. A successful return establishes
delivery to the approved control, **not independent readback of the document**. Visual confirmation
on the target PC remains part of acceptance.

Writing **replaces the editor's existing text**. No automatic file Save or Undo is provided. Cypher
does not read existing document text or persist workflow text. Notepad itself may keep its own
session/autosave data; this is not a promise about the target app's storage.

The last executed workflow checkpoint stores only schema, random workflow ID, state, step counts,
and timestamps. It excludes app names, window titles, text, paths, payload hashes, and reusable
approvals. A checkpoint is never treated as an executable plan.

After interruption, Cypher marks a previously RUNNING checkpoint INTERRUPTED and does not resume
anything. Inspect the apps and submit a new plan for only the work still needed. Do not blindly
repeat a workflow: its completed effects may remain.

The 60-second execution budget is checked before actions. Polling is bounded, but a synchronous
Windows/UI Automation call cannot be forcibly interrupted by this preview. Stop remains cooperative;
it is not a guarantee that a hung application call returns within that budget.

## Diagnostics and rollback

First use `Show workflow status` inside Cypher. Alternatively, from normal PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\Cypher\CorePreview\manage_cypher_core_preview_windows.ps1" workflow-status
```

For the prior working no-ID workflow, reinstall from the retained **v0.8.8.1** folder. The manager's
existing `rollback` command still targets the older **v0.6.3 resident host**, not v0.8.8.1.

This package is not code-signed. SHA-256 checksums establish package integrity, not publisher identity.
See `RELEASE_NOTES_MULTISTEP_WORKFLOW.md` for the verification boundary.
