# Cypher v0.8.6.0 Bounded UI Automation Preview 1

This release adds the first bounded in-application action surface to the compiled Cypher resident
host. It is intentionally narrower than general computer use.

## Added

- List actionable Windows UI Automation controls in one currently visible window belonging to a
  human-registered application.
- Stable, session-fresh `uia-...` control IDs with metadata-only labels, control type, enabled state,
  on-screen state, and supported action patterns.
- One native approval workflow for exactly one Invoke, Toggle, Select, Expand, or Collapse action.
- Approval binding to the registered app, executable hash and metadata, window, control, action,
  expiry, and canonical fingerprint.
- Immediate pre-execution revalidation and one-time approval consumption.
- State verification for Toggle, Select, Expand, and Collapse. Invoke reports only successful UIA
  request delivery, not an unverified downstream application result.
- A new `INSTALL_CYPHER_BOUNDED_UI_AUTOMATION.cmd` launcher and transactional Windows installer
  assembly checks.

## Hard boundary

This preview does not expose text entry, ValuePattern, TextPattern, password/edit/document controls,
raw mouse or keyboard events, screen coordinates, screenshots, arbitrary executables, shell commands,
multi-action macros, persistent approvals, or unattended operation. Sensitive system and password-
manager executables are denied even if a person attempts to register them.

## Verification status

The source and packaged Python regression suites, native-host lexical checks, checksum manifest, and
ZIP integrity are release gates. The target Windows PC must still compile the WPF host with the local
.NET Framework assemblies, pass the executable self-test, and complete harmless Calculator/Notepad
acceptance tests before this becomes the installed baseline.

## Install

Extract the whole ZIP into a new folder and run:

```text
INSTALL_CYPHER_BOUNDED_UI_AUTOMATION.cmd
```

The installer does not widen broker roots, enable Hermes built-in tools, download models, request
administrator rights, or remove the cooperative rollback copy.
