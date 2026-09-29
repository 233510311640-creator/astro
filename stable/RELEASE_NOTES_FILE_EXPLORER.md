# Cypher 9.5.0 — File Explorer

11 September 2026. Core Preview 9.5.0; Python distribution 0.9.5a1.

This bundle extends the granted-folder workflow from file changes to file discovery and reading.
It does not require a model call, research provider, plugin or new folder grant.

- Adds literal, case-insensitive filename search, optionally scoped to a relative subfolder.
- Extends directory listing to relative subfolders and replaces raw metadata JSON with readable results.
- Adds UTF-8 text viewing for the existing safe text extensions, up to 32 KiB and 200 displayed lines.
- Shows relative paths, metadata, read byte count and a SHA-256 digest of the complete bytes read.
- Checks search budgets and Stop during enumeration; reports partial coverage instead of claiming
  that an incomplete scan found every match. Search does not open user file contents.
- Rechecks grants before each scanned directory and before returning results. Existing broker rules
  reject protected names, hidden/system paths, links/reparse points and paths outside a grant.
- Caps the read itself, checks opened-file identity and metadata before/after reading, and discards
  text if the file changes, permission is revoked, Stop occurs or validation fails.
- Keeps file contents out of model history. Native progress distinguishes read-only requests from
  modification plans; read cancellation does not claim a rollback.
- Packages the new browser module in the independently pinned file worker. The native installer
  fixture exercises search, listing, reading and cancellation before replacing the installed host.

File execution/undo, capability broker, permission storage, payload protection, runtime worker,
research logic and Windows workflow engines are unchanged from 9.4.0. Native file-host edits only
change read-only progress/error wording; approval/execute callbacks retain their existing behavior.
The shared process client changes only its file-worker integrity pin.

The user reported completion of the 9.4.0 handoff. No benchmark screenshot or numerical measurements
were supplied in that reply, so this release does not assert a performance result or tune Ollama.
Previously verified 9.3.0 organization, undo and pre-approval cancellation remain recorded evidence.

This is not OS-level containment against malicious same-user filesystem mutation. Path checks,
bounded reads and identity checks reduce accidental/routine races; they are not a claim that all
filesystem races are eliminated. Existing operating-system and approved-root trust assumptions apply.
Text-view digest is an identity marker, not an authenticity signature or proof of unchanged future content.

See FILE_EXPLORER_SETUP.md for one new Windows check. No repeat organization/undo/Stop exercise,
paid API, model download, new generation, countdown, retry loop or Computer Use is required.
