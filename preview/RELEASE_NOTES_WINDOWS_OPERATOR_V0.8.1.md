# Cypher v0.8.1 Windows Operator Preview 1 — Release Notes

**Release date:** 22 August 2026  
**Release type:** functionality-first Windows operator alpha

## Added

- six conditional MCP tools for Windows status, registered apps, top-level windows, foreground
  observation, registered-app launch, and window focus;
- native Win32 top-level window enumeration with visible title, class, process, minimized state and
  bounds;
- explicit foreground-window observation and post-focus verification;
- a human-managed exact-executable allowlist with no model-supplied arguments;
- automatic registration of available Notepad, Calculator, Paint and File Explorer executables;
- a Windows app manager and combined one-click preview installer;
- metadata-only audit events that do not persist window titles.

## Fixed

- Windows PowerShell 5.1 failure-receipt validation now counts JSON properties correctly instead of
  falsely reporting that valid receipts are missing metadata.

## Deliberately not included

- arbitrary shell or terminal execution;
- simulated keyboard or mouse input;
- screenshot capture or OCR;
- process termination;
- UI redesign or voice work.

The Windows control implementation follows the documented `EnumWindows`, `GetForegroundWindow`, and
`SetForegroundWindow` behavior. Since Windows may legitimately deny a focus request, Cypher reports
the observed result rather than claiming success from the request alone.

## Verification

- 183 source tests pass on the build system;
- the Windows package will rerun all included tests and the current-user DPAPI preflight before it
  changes the resident installation;
- final Win32 behavior still requires the three acceptance prompts in
  `WINDOWS_OPERATOR_PREVIEW_SETUP.md` on the target Windows PC.
