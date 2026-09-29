# Cypher v0.8.9.2 — Fast Windows Workflow Preview

**Historical 8.5.2 instructions. For the current 8.5.3 package, use [Hosted window fix setup](HOSTED_WINDOW_FIX_SETUP.md).**

Core Preview **8.5.2** removes the artificial two-second arming pause. Review the plan and approve once; execution proceeds directly to target checks and actions. Stop remains available while a workflow is active. No extra confirmation, countdown, or test mode is added to normal use.

## Install

1. Keep your working **v0.8.9.1 / Core Preview 8.5.1** folder for reinstall rollback.
2. Extract this ZIP into a **new folder**. Finish or deny any active Cypher request.
3. Run **INSTALL_CYPHER_MULTISTEP_WORKFLOW.cmd** normally, not as administrator.
4. Let the installer finish its source tests, native behavioral tests, host compilation, and host self-test. Open Cypher with **Ctrl+Alt+Space** and check for **CORE PREVIEW 8.5.2**.

No model download, evaluator run, app registration, or permission change is needed.

## One normal workflow check

Keep exactly one restored Notepad window with a **blank, disposable document**. This test replaces its text. Submit:

```text
Workflow:
Open Notepad and write: Cypher fast workflow passed.
Minimize Notepad
Restore Notepad
```

Review the four actions, then **Approve once** and let them finish. Expect **COMPLETED · 4/4**, the same Notepad window restored, and the exact text `Cypher fast workflow passed.`. There must be no ARMING screen or fixed two-second countdown. App startup, target checks, and Windows state changes can still take time.

A short confirmation of the result is enough; send a screenshot only if something differs. Do not repeat all the old acceptance tests.

## Calculator follow-up

With one Calculator window open, submit:

```text
Workflow:
Minimize Calculator
Restore Calculator
```

If it reaches approval, approve once. Expected normal result: **COMPLETED · 2/2**, Calculator restored.
If it rejects or fails with **AMBIGUOUS_WINDOWS**, share the complete diagnostic. It now names the app, reports the number of matches, and shows up to five window handles, process IDs, classes, owner handles, minimized states, and cloak flags. No window titles or document text are included in these diagnostic rows. They are displayed in memory, not added to the saved workflow checkpoint.

**The earlier Calculator ambiguity is not claimed fixed.** Hidden/cloaked or owned windows remain candidates. Cypher will not silently ignore them, select the first match, or change app permissions.

## Stop without a countdown

Stop can cancel pending app-readiness polling and prevents subsequent actions when cancellation is observed. A native Windows/UI Automation call already running cannot be forcibly interrupted. A completed action is not undone. If Stop arrives after the final verified step, COMPLETED remains the correct result.

Very short tasks can finish before you click Stop; this is expected and does not justify reintroducing a production delay. The installer exercises cancellation after a completed step using a fake executor and a deliberate wait **inside the self-test only**. That engine test does not substitute for a live Windows cancellation observation.

If a native step was entered but has no verified receipt, the result warns that the app may have changed. If Stop arrives before the executor is entered, that step is not counted as started.

## Rollback

Reinstall the retained **v0.8.9.1** package. The older manager's `rollback` command still targets v0.6.3; do not use it to return specifically to 8.5.1.

See [release notes](RELEASE_NOTES_FAST_WORKFLOW.md) for implementation and verification details.
