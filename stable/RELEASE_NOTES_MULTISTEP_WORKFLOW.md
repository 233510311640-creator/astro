# v0.8.9.0 — Multi-step Windows Workflow Preview 1

**Date:** 27 August 2026  
**Core identifier:** `0.7.0-core-preview8.5.0`  
**Python package identifier:** `0.8.9a1`  
**Status:** source-validated candidate; native Windows gates pending

## Baseline

Recovered the exact v0.8.8.1 archive with SHA-256:

`4bd2d253ec22a95f6d830b8d1ea94a02866432b7dd62995f0740cd70a2ef5322`

Its 120 manifest entries verified and its original 212 Python tests passed before changes.
The supplied Windows screenshot shows Core Preview 8.4.1 delivering the approved text to the existing
Notepad editor. That screenshot does not prove the no-window launch path, every denial scenario,
or the new multi-step implementation.

## Changes

- Explicit ordered `Workflow:` recipes, with Open, Write in, Focus, Minimize, and Restore actions.
- One complete native approval preview, including all text, with a 60-second expiry. The approval
  is atomically consumed, bound to step order, app identities, selection rules, and exact text.
- Up to six expanded steps across three registered apps. Unsupported lines reject the whole plan.
- App/executable/window revalidation at execution. An existing window cannot silently be replaced
  by another. A fresh window may be bound only as the result of an approved Open step.
- The existing packaged-app identity and title-stability fixes remain. Writes use the proven
  managed UI Automation ValuePattern path, without keyboard, clipboard, shell, or screenshot fallback.
- Full accessibility scans for automatic editor selection: truncation or unreadable elements now
  prevent the new workflow route from asserting that an editor is unique. Existing ID-based routes
  retain their bounded inventory behaviour.
- Progress, cooperative Stop, partial-success reporting, pre-action checkpoints, and no retry or
  restart replay. No automatic save, append, undo, close, or process termination was added.
- Metadata-only `Show workflow status` and manager `workflow-status`.
- Native workflow logic separated from the WPF shell. The installer requires and compiles all
  source parts and tests the real workflow engine with a fake Windows executor before installation.
- Exact registry IDs can disambiguate display-name collisions. Ambiguous names otherwise refuse.

## Verification record

| Check | Result / boundary |
| --- | --- |
| Untouched baseline | 212 Python tests passed; exact archive hash and 120 manifest entries verified. |
| Integrated Python suite | 217 tests discovered; 216 passed and one Windows-only compiler test skipped in this Linux environment. |
| C# source checks | Balanced lexical structure for all five source files; WPF XAML parses; route, consent, identity, checkpoint, and installer integration checks pass. This is not a C# compiler result. |
| Native behavioral harness | Added 23 scenarios, numbered 100–122, for the production parser/runner/approval/checkpoint code with a fake Windows adapter. Must compile and pass on Windows. Not executed here. |
| Complete Windows host | Must compile and pass `--self-test` on the target PC before the installer switches executables. Not executed here. |
| Real app acceptance | Pending: deny, approve, exact visible text, minimize/restore/focus, two-app plan, Stop, ambiguity, and restart behaviour. |
| Archive | Package manifest and ZIP integrity are checked after generation and again after clean extraction. See the accompanying checksum manifest. |

The fake adapter tests execution ordering and the consent/recovery state machine; it is not evidence
that the native Windows adapter worked. A successful `SetValue` call is delivery evidence, not text
readback. The package must not be described as a completed end-to-end Windows release until the
target-PC checks succeed.

## Native self-test scenarios

100 parser expansion; 101 literal text and routing; 102 invalid/oversized recipes; 103 ordered execution;
104 replay (including non-text actions); 105 wrong fingerprint; 106 expired approval; 107 denial;
108 changed text; 109 pre-cancel; 110 stop after one action; 111 target validation failure;
112 failed postcondition; 113 execution exception; 114 pre-action checkpoint failure;
115 post-action checkpoint failure; 116 time budget; 117 stop at the pre-action boundary;
118 concurrent approval claims; 119 real metadata-store roundtrip/privacy;
120 interruption reconciliation without replay; 121 unexpected checkpoint fields;
122 inconsistent completed checkpoint.

## Known limits and rollout

Use disposable documents. Focus can be refused by Windows. Accessibility trees may change and cause
a refusal, especially while switching tabs or opening dialogs. Do not change the target apps during
execution. Same-user application identity/accessibility metadata is not a security boundary against
a malicious local process impersonating an app.

Stop does not force-cancel a synchronous UI Automation call. The execution time budget is enforced
at action boundaries; a blocked native call can outlive it. Failed or cancelled workflows may have
completed effects, and an unverified current action may have a partial effect.

Keep v0.8.8.1 for reinstall rollback. Existing v0.6.3 rollback semantics are unchanged. No app
registration, text-entry authority, model download, network research, microphone permission, or
unattended background recipe is introduced.

## API references consulted

- [ShowWindowAsync](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindowasync):
  posting a state-change request is distinct from checking its resulting state.
- [SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow):
  Windows can deny foreground activation; the adapter checks foreground equality.
- [UI Automation threading](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-threading-issues):
  workflow automation runs off the WPF UI thread; app elements are reacquired for execution.
