# Cypher v0.8.9.2 / Core Preview 8.5.2

## Reason for this release

The user confirmed Core Preview 8.5.1's normal workflow and cancellation during its two-second arming window. That pause was useful for a manual test, but the user requested that it not delay routine work. This release removes it and improves cancellation inside existing workflow waits.

The previously accepted 8.5.1 remains the Windows baseline until this candidate is installed and checked. This is a focused workflow reliability increment; it does not add voice, vision, durable chat memory, or unrestricted desktop control.

## Changes

- **No approval countdown.** The public runner directly consumes approval, checks cancellation and budget, revalidates targets, and executes. There is no arming setting, timer, extra user step, or production test delay. WPF progress handoffs still yield to pending input at Background priority, and queued progress cannot overwrite STOPPING.
- **Cancellable observation waits.** Editor-readiness, app-launch observation, minimize/restore verification, and focus verification use the same cancellation-aware wait helper. It wakes on Stop and bounds each wait by the remaining 60-second execution budget. An already-ready state incurs no polling delay. This does not interrupt a synchronous OS or accessibility call already underway.
- **Final text check.** The existing app/window/control/pattern validation path now accepts an optional workflow callback. Workflow writes invoke it after the final read-only check and immediately before `ValuePattern.SetValue`. Other existing callers retain their previous behavior. Text is still never read back, saved, or automatically undone.
- **Accurate pre-executor cancellation counts.** If cancellation or a progress failure occurs after the intent checkpoint but before the executor is called, the final started count is restored to the number of earlier entered steps. Once the executor is entered, an unverified step remains conservatively marked as potentially changed. The saved RUNNING intent continues to protect recovery if a process dies at this boundary.
- **Actionable ambiguity diagnostics.** Multiple matching windows still cause AMBIGUOUS_WINDOWS. Only on that failure, Cypher adds the registered app label, match count, and up to five bounded metadata rows: HWND, PID, class, owner HWND, minimized state, and DWM cloak flags. Display strings are length-bounded and control characters are replaced. No titles, document text, executable paths, registry changes, or extra observation is added to successful runs. Diagnostics are not written to the checkpoint.

## Calculator evidence and limits

The earlier screenshot established a failure after two verified steps, at a Calculator action, with AMBIGUOUS_WINDOWS. It did not identify the extra window's class, owner, or cloak state. The cause remains unresolved; this release does not claim to reproduce or fix it.

Windows exposes cloak state separately from its ordinary visibility flag. The new read-only diagnostic uses that documented state, but does not use it to discard candidates or relax exact identity checks. A hidden-window explanation remains a hypothesis until target-PC metadata supports it. See Microsoft's [DWMWINDOWATTRIBUTE reference](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute), [DwmGetWindowAttribute reference](https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmgetwindowattribute), and [IsWindowVisible reference](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-iswindowvisible).

The wait helper uses the cancellation token's wait handle. WPF input responsiveness retains the existing lower-priority progress dispatch. References: [CancellationToken.WaitHandle](https://learn.microsoft.com/en-us/dotnet/api/system.threading.cancellationtoken.waithandle), [WaitHandle.WaitOne](https://learn.microsoft.com/en-us/dotnet/api/system.threading.waithandle.waitone?view=netframework-4.8.1), [DispatcherPriority](https://learn.microsoft.com/en-us/dotnet/api/system.windows.threading.dispatcherpriority).

Owner handles are reported through the read-only [GetWindow / GW_OWNER query](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindow); ownership is not used as permission to choose a different target.

## Verification

- Local source/regression suite: **221 discovered, 220 passed, one Windows-only compiler test skipped**.
- Lexical delimiter checks passed for all five C# source files; the suite also includes the existing XAML parsing check. Neither is a native compiler result.
- Existing native behavioral harness expanded from 25 to **30 cases (100–129)**. Cases cover immediate public-runner entry, cancellation during a simulated observation after an earlier verified action, accurate partial receipts, replay refusal, late Stop after final completion, budget-limited waiting, pre-executor cancellation counts, bounded diagnostics, and successful polling. Existing parser, approval, checkpoint-failure, and restart tests remain.
- The full installer still runs the native harness and compiled-host self-test before replacing the installed host. The deliberate slow observation used to test cancellation exists only in the fake executor.
- **No C# compiler, .NET Framework runtime, WPF, or Windows desktop is available in the Linux workspace.** Native compilation, execution of those 30 cases, and real-app acceptance were not run here. Source assertions and delimiter checks are not substitutes for these gates.
- The user confirmed the prior 8.5.1 normal 2/2 result and arming cancellation 0/2 result. Those observations do not establish this new build's live behavior, cancellation inside an in-flight native call, or Calculator resolution.

## Preserved boundaries

The six-step/three-app limit, one-time full-plan approval, expiry, exact app/window/control revalidation, human-managed text permission, metadata-only checkpoint schema, no retry/replay, no automatic undo, and standard-user execution are unchanged. No new model, network service, raw keyboard/mouse injection, clipboard operation, or shell capability is introduced.

Use [FAST_WORKFLOW_SETUP.md](FAST_WORKFLOW_SETUP.md) for the focused Windows checks. Keep 8.5.1 for reinstall rollback.
