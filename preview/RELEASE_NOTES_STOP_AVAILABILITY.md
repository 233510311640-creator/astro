# v0.8.9.1 — Multi-step Windows Workflow Stop Fix

**Date:** 27 August 2026 (UTC)  
**Core identifier:** `0.7.0-core-preview8.5.1`  
**Python package identifier:** `0.8.9a2`  
**Status:** source-validated patch candidate; native Windows patch acceptance pending.

## Evidence and reason for the patch

The target-PC screenshots demonstrate the v0.8.9.0 single-app and two-app workflows, visible text delivery, Minimize/Restore/Focus, denial, and pre-approval Stop. A repeated Notepad-only workflow completed all six steps without demonstrating cancellation. A separate attempted Stop test failed after two verified steps with `AMBIGUOUS_WINDOWS` while handling Calculator.

Source inspection found that Stop is wired to the cancellation token while a workflow is active, and disabled after terminal completion or failure. The screenshots do not establish that the control was disabled during execution. The confirmed usability gap is the lack of a dependable opportunity to click Stop after approval for short recipes. This patch addresses that gap; it does not claim a proven defect in token cancellation or a fix for the Calculator failure.

Baseline archive SHA-256: `a314b1b7a25c56a94c2423778719edbebd54fc4d6095a31ae2af6116cfa9a7b6`.
All 127 baseline checksum entries verified. The baseline suite ran 217 tests: 216 passed and the Windows compiler test was skipped on Linux.

## Changes

- Consume the exact one-time approval, then provide a two-second cancellable Stop window on the background worker before target revalidation or any app action.
- Show **ARMING · STOP AVAILABLE**, keep Stop enabled, and explain the pause in the full plan preview. The existing 60-second execution budget includes this delay.
- Wait on the cancellation token's wait handle, so Stop releases the wait promptly. A cancellation here records zero started/verified steps and discards the in-memory text.
- Revalidate the app/window after the delay; a changed or ambiguous target is still rejected.
- Dispatch workflow progress at WPF Background priority so pending input can be serviced first. Suppress stale progress after cancellation so it does not overwrite STOPPING.
- Preserve the existing native adapter, app registry, permissions, approval fingerprint, expiry, replay refusal, checkpoint schema, and native-call cancellation limitations.

## Verification

| Check | Result or boundary |
| --- | --- |
| Integrated Python suite | 218 discovered; 217 passed, one Windows compiler test skipped. |
| C# source structure | Lexical delimiter checks passed for all five C# files; existing WPF XAML parsing checks passed. These are not compiler results. |
| Native engine scenarios | Existing 100–122 retained; 123 tests cancellation in the real production arming path with zero executor calls; 124 tests that validation/execution waits until the arming window ends. Must run on Windows. |
| Pre-action cancellation coverage | Scenario 117 still targets the checkpoint/action boundary without the new arming delay; it has not been replaced by the easier pre-action arming test. |
| Native compilation and WPF execution | Not run in this Linux environment. Required installer gates before the executable switch. |
| Target-PC patch acceptance | Pending: ARMING visibility, clickable Stop, CANCELLED 0/2, unchanged Notepad, saved cancelled counts, and normal 2/2 completion. |
| Mid-execution cancellation | Still requires separate live evidence; cancellation in ARMING is not presented as proof of interrupting an action already underway. |
| Calculator ambiguity | Unresolved; refusal remains enforced. No window-selection workaround was introduced. |

The installer retains its native compiler and executable self-test gates. Passing Python/source checks does not establish that the new C# code compiled or that the Windows patch passed acceptance.

## API references

The cancellation wait uses [WaitHandle.WaitOne](https://learn.microsoft.com/en-us/dotnet/api/system.threading.waithandle.waitone?view=netframework-4.8.1). Progress dispatch uses the priority-taking [Dispatcher.Invoke overload](https://learn.microsoft.com/en-us/dotnet/api/system.windows.threading.dispatcher.invoke?view=windowsdesktop-8.0) and [DispatcherPriority](https://learn.microsoft.com/en-us/dotnet/api/system.windows.threading.dispatcherpriority). These references describe API semantics; they are not evidence that this build ran on the user's PC.
