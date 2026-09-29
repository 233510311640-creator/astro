# Cypher v0.8.7.2 Packaged-App Text Entry Preview 1 Fix 2

This release builds on the verified v0.8.6 bounded UI Automation baseline. It adds exact packaged-app
identity and one narrowly permissioned Set Text action without introducing raw computer control.

Fix 2 keeps the earlier compile correction and repairs packaged-window resolution observed on
Windows 11 Notepad. The host now queries the documented process `AppUserModelID` when a top-level
window does not publish its own property, then resolves an exact human-registered packaged identity
before attempting `MainModule` access. This avoids treating a protected package executable as the
stable launch identity. Ordinary unpackaged apps still require an exact registered executable path.
Text entry remains available only through the documented managed writable `ValuePattern`.

## Added

- Strict version-2 Windows application records with optional exact `AppUserModelID` and independent
  `allow_text_entry` capability.
- Valid version-1 registry migration with both new authority fields disabled by default.
- Human-side commands to set or clear one packaged identity and separately enable or disable text
  entry for one registered app, each protected by an exact confirmation phrase.
- Exact top-level-window AppUserModelID resolution through the Windows property store, followed by
  documented process-AUMID fallback for windows that inherit their packaged identity.
- AUMID-first packaged-app matching against the human-managed record; ordinary apps retain strict
  exact-executable resolution.
- Safe observation diagnostic codes for stale targets, unverified identity, unavailable Windows UI
  Automation, and other bounded failures; raw exception text is not displayed.
- `set-text` discovery for a fresh safe Edit/Document control only when the registered app has text
  entry enabled and Windows UI Automation reports a writable value pattern.
- One-time approval binding for the app, executable metadata and hash, packaged identity, window,
  control, action, text length and text SHA-256, expiry, and canonical fingerprint.
- Immediate revalidation followed by exactly one `ValuePattern.SetValue` call.

## Privacy and safety boundary

- Existing Value/Document content is never read.
- The requested text is limited to 500 printable single-line characters and remains only in the
  pending in-memory action. Denial, expiry, execution, shutdown, or restart discards it.
- Password controls, sensitive field labels, sensitive processes, disabled capabilities,
  unregistered apps, stale IDs, changed targets, and replayed approvals fail closed.
- No SendKeys, raw keyboard or mouse input, clipboard, coordinates, screenshots, shell commands,
  arbitrary paths, multi-control macros, persistent approval, or unattended continuation exists.
- Built-in seeding may discover an exact packaged identity but does not silently enable text entry.

## Verification status

All 210 Python/source regression tests pass. The transactional Windows installer also
requires local .NET Framework compilation, the native executable self-test, and authenticated Hermes
capability checks before replacing the resident host. This candidate becomes the verified installed
baseline only after harmless target-PC Notepad acceptance confirms migration, explicit opt-in, denial,
fresh approval, SetValue delivery, expiry, replay rejection, stale-control rejection, and sensitive-
field rejection.

## Install

Extract the complete ZIP into a new folder and run:

```text
INSTALL_CYPHER_PACKAGED_APP_TEXT_ENTRY.cmd
```

After installation, close Cypher and run these human-side registry steps from the extracted folder:

```text
MANAGE_CYPHER_WINDOWS_APPS seed-builtins
MANAGE_CYPHER_WINDOWS_APPS list
MANAGE_CYPHER_WINDOWS_APPS set-text-entry notepad on
MANAGE_CYPHER_WINDOWS_APPS list
```

Review and type the exact confirmation phrase requested by the third command, then restart Cypher.
The installer and manager do not widen file roots, enable Hermes built-in terminal/file tools,
download models, request administrator rights, or remove the cooperative rollback copy.
