# Cypher v0.8.9.3 — Hosted Window Fix

Core Preview **8.5.3** is a focused candidate for the Calculator ambiguity shown in the latest diagnostic. Windows reported both a minimized application frame and a shell-cloaked content window. This update requires proof that the content window belongs to the bound frame before treating them as one action target. Other matching windows still cause a refusal.

The two-second arming pause stays removed. No new models, permissions, or administrator access are needed.

## Install

1. Retain your **v0.8.9.2 / Core Preview 8.5.2** folder for reinstall rollback.
2. Extract this ZIP into a **new folder**. Finish or deny any active Cypher request.
3. Run **INSTALL_CYPHER_MULTISTEP_WORKFLOW.cmd** normally, not as administrator.
4. Allow the installer to complete its checks. It compiles/runs the native behavioral harness and the full host self-test before replacing the installed host.
5. Open Cypher with **Ctrl+Alt+Space** and check for **CORE PREVIEW 8.5.3**.

The package uses the same plain ZIP format as the successful 8.5.2 extraction replacement.

## One focused Calculator check

Keep exactly **one Calculator window** open, with no extra Calculator windows or dialogs. **Restore it manually first** if the failed run left it minimized. Cypher needs to observe the content window attached to that frame before preparing this plan. It will not infer a pairing from two already-detached windows.

Submit:

```text
Workflow:
Minimize Calculator
Restore Calculator
```

Review the two actions and choose **Approve once**. If a hosted pair was proved, the approval details identify its content HWND/PID. Expected result: **COMPLETED · 2/2**, with the same Calculator window minimized then restored. No arming screen or fixed countdown should appear.

Send the result and confirm whether Calculator finished restored. If approval or execution fails, send the full diagnostic instead; do not keep resubmitting it or change permissions. A failure after an attempted step may have left the app changed.

No text is written in this test. No Stop race or repeat of the earlier acceptance sequence is required.

## Scope and limits

- Pairing is held in memory for this plan only. It is not saved as a preference or reusable approval.
- An unknown extra window, changed identity, missing bound frame, or unproved detached companion still rejects. A cloak flag by itself never authorizes selection.
- An app that is already minimized when a fresh request is prepared may still reject. Manually restore it before the new request; this release does not persist a pairing across requests or restart.
- Stop prevents later actions when cancellation is observed and wakes pending observation waits. It does not interrupt a synchronous native call already running or undo completed effects.
- The broad Windows milestone remains a preview. Live mid-execution cancellation and crash/no-replay observations remain separate acceptance gaps.

## Rollback

Reinstall your retained **v0.8.9.2** package. The older manager's `rollback` command targets v0.6.3, not specifically 8.5.2.

See [release notes](RELEASE_NOTES_HOSTED_WINDOW_FIX.md) for implementation and verification details.
