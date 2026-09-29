# Cypher v0.8.9.1 — Stop availability fix

> Historical 8.5.1 instructions. Core Preview 8.5.2 removes this arming pause at the user's request. Use [FAST_WORKFLOW_SETUP.md](FAST_WORKFLOW_SETUP.md) for the current build; do not repeat this historical countdown test.

Core Preview **8.5.1**. This patch is a source-validated Windows acceptance candidate.

## Install

1. Keep the working v0.8.9.0 folder for reinstall rollback.
2. Extract this complete ZIP into a new folder.
3. Finish or deny any active Cypher request. Run **INSTALL_CYPHER_MULTISTEP_WORKFLOW.cmd** normally, not as administrator.
4. The installer must pass its Python checks, native workflow tests, host compilation, and host self-test before switching the installed executable.
5. Open Cypher with **Ctrl+Alt+Space** and check for **CORE PREVIEW 8.5.1**.

Do not download models, rerun the brain evaluator, enable new apps, or change text-entry permissions for this patch.

## First acceptance test: Stop after approval, before the first action

Keep exactly one disposable Notepad window open and restored. Make sure the Stop button is visible.

```text
Workflow:
Minimize Notepad
Restore Notepad
```

Review the two actions and choose **Approve once**. During **ARMING · STOP AVAILABLE**, click **Stop**.
The arming period lasts two seconds and no app action starts during it.

Expected:

- **CANCELLED · 0/2 steps verified** with **STOP_REQUESTED**.
- Notepad remains restored and its text is unchanged.
- `Show workflow status` reports **CANCELLED**, **0/2 verified**, **0 started**.

Send the Cypher result and confirm the window stayed unchanged. A completed 2/2 run means Stop was too late; it does not demonstrate cancellation. A compiler error, disabled button during ARMING, or unexpected action is not a pass.

This test demonstrates cancellation after approval but before app execution. It does not prove interruption of a native call already in flight or cancellation after several steps have executed.

## Normal execution check

Submit the same recipe with a fresh approval and let it run. After the two-second Stop window, Notepad should minimize and restore, with **COMPLETED · 2/2 steps verified**. No document text is edited by this recipe.

## Preserved limitations and rollback

- Stop remains cooperative. A synchronous native call already underway may finish and cannot be forcibly interrupted by this patch.
- Completed actions are not undone. No automatic retry, save, replay, or persistent approval is added.
- The earlier Calculator `AMBIGUOUS_WINDOWS` failure is not fixed or bypassed. Multiple matching windows still reject preparation or stop later execution. Use only Notepad for this cancellation test.
- To return to the earlier multi-step build, reinstall from the retained v0.8.9.0 folder. The old manager `rollback` command still targets v0.6.3.

See `RELEASE_NOTES_STOP_AVAILABILITY.md` for implementation details and verification boundaries.
