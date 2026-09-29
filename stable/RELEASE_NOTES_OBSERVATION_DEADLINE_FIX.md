# Core Preview 9.2.11 — Observation Deadline Fix

Package **v0.9.2.11** · Python package **0.9.2a12** · 8 September 2026

The reported 9.2.10 installation passed 189 Python research tests, compiled the host, then stopped
at native self-test **126** before replacing the resident host. The refined UI was not installed.
This release corrects a timing defect in the workflow wait exercised by that check and retains the
refined graphite/violet interface from 9.2.10.

## Diagnosis and correction

Test 126 requests a ten-second observation interval inside a 25 ms execution budget. It requires
`TIME_BUDGET_EXCEEDED` and completion within two seconds. The screenshot identifies that assertion,
but does not show whether the fault-code branch or elapsed-time branch failed.

The old implementation waited once, then assumed that the requested interval had elapsed. Windows
waits can return before the requested duration because of clock resolution, as documented in
[Microsoft's wait-functions reference](https://learn.microsoft.com/en-us/windows/win32/sync/wait-functions).
An early return before the budget deadline could make the method return without the required fault.
That concrete defect is consistent with the reported code; no target-PC timing trace was captured.

The correction uses one monotonic observation deadline, capped by the existing execution budget.
After an early wake it checks cancellation and the budget, then waits only for the remaining time.
Stop still wakes the cancellation wait; expiry prevents later actions. The original real-clock
case 126 and its two-second ceiling remain unchanged. No timer-resolution change, busy zero poll,
extended execution budget, self-test bypass, automatic action retry or new approval delay is added.

An internal clock/wait constructor lets the compiled behavioral harness simulate precise wake
conditions. Production uses the normal constructor, which binds a Stopwatch and the cancellation
token's WaitHandle directly. Input, settings, web content and model output cannot select the seam.

## Validation

- Python suite: **415 discovered, 414 passed, one native Windows compiler test skipped on Linux**.
- Research: **189 passed**, including the run with EncodingWarning treated as an error.
- Actual C# workflow engine and behavioral harness compiled and ran under Linux Mono 6.8:
  **cases 100–147 passed**, including the original real-clock budget and Stop cases.
- Eight new deterministic cases exercise an early budget wake, repeated early observation wakes,
  Stop after a wake, already-exhausted budget, oversleep, fractional-millisecond remainder,
  invalid intervals and cancellation priority.
- Negative control: restoring the delivered 9.2.10 single-wait method, with only its clock/wait
  calls routed through the same test seam, fails the new early-wake case **140**. The corrected
  method passes. This executes C# behavior rather than inferring correctness from source strings.
- The source package includes `scripts/verify_workflow_mono.py` to repeat the supplementary C#
  harness with an existing local Mono runtime. The runtime/compiler is not shipped or installed.
- All packaged file hashes and bytes are verified after fresh extraction; the Windows launcher
  retains CRLF formatting. Research worker hash and host pin remain unchanged.

The complete WPF host and Windows installer cannot run in this Linux environment. Native layout,
Windows clock behavior, target-PC installation and DPI/appearance remain pending. The installer
still executes its full native self-test, WPF layout test and owned-worker test before host
replacement. The same error should not be labelled fixed on the target PC until that gate passes.

## Retained behavior

The refined UI, prompt cards, Send/Stop, approvals, hotkey, saved geometry and pin preferences,
Ollama startup, research worker, model budgets and provider rules are retained. The academic
discovery-quality milestone remains open. Historical 9.2.10 preview images are design references,
not screenshots of this release running on Windows.

## Install

1. Keep your current working package for rollback and finish any active request.
2. Extract the complete new ZIP into a fresh folder.
3. Run **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally, not as administrator.
4. After successful installation, open with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.2.11**.

No separate status checker or repeat of the academic question is needed. The next useful result is
successful installation and the actual refined interface. If installation stops, retain the exact
new error rather than bypassing the check.
