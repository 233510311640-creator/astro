# v0.4.0 security boundary and limitations

## Hermes Sandbox actions

- One fixed existing sandbox root.
- Direct operations are limited to bounded listing and small UTF-8 text reads.
- Mutations start as immutable SHA-256-fingerprinted plans with a 60-minute human-review window.
- No proposal changes the filesystem.
- Approval exists only in the separate human-side CLI and opens a fresh 10-minute execution window.
- Apply is single-use and rejects unapproved, changed, expired, failed, executed, or wrong-root plans.
- Create and move never overwrite existing targets; replacement rechecks the original hash.
- Human-side undo refuses to overwrite later changes or remove nonempty directories.

## Real-folder inventory

- No inventory root is enabled by default.
- Roots can be added or removed only through a separate human-side command that requires typed confirmation.
- The model cannot call the allowlist manager or change its configuration.
- Drive roots, filesystem roots, the user-profile root and its parents, AppData, system directories, credential directories, hidden/system roots, protected names, links, junctions, and reparse points are rejected.
- Roots cannot overlap, and all relative paths are checked against traversal and reparse-point escape.
- Inventory operations use directory entries and filesystem stat metadata only. They do not open target files or read content bytes.
- Recursive work is capped by depth, results, examined items, examined directories, and entries per directory.
- Hidden/system items, protected names, unavailable objects, and links are skipped.
- Filenames and paths returned by inventory are explicitly treated as untrusted data, never instructions or permission.
- Inventory has no create, replace, copy, move, rename, delete, hash, thumbnail, EXIF, archive-inspection, or project-file parser.
- Graphic candidates are classified from extensions only; classification is not proof that a file is used by graphic software or safe to reorganize.

## Privacy

- Approved inventory roots reveal relative filenames, paths, types, extensions, sizes, and modification timestamps to the local model and the local Hermes session.
- Inventory audit records contain root IDs, counts, limits, and outcomes—not scanned filenames or file contents.
- The allowlist file stores approved root IDs and absolute root paths, not inventories.
- Proposed sandbox text and reversible pre-edit snapshots remain in `%LOCALAPPDATA%\LocalAssistantBroker\action_state.db`.
- A filename itself can contain misleading instructions. Names are untrusted data and never grant permission.
- BitLocker protects powered-off data but does not isolate an unlocked Windows account.
- A malicious process already running as the same Windows user can access user files independently; this broker is not an antivirus or OS security boundary.

## Absent

No raw shell, process control, arbitrary code, web, browser, UI automation, credentials, messaging, scheduling, administrator access, unrestricted file API, or real-folder write exists in this release. MCP sampling and elicitation are not required and should remain disabled.

Remove the integration immediately if the tool count is not exactly twelve, a content reader or real-folder mutation tool appears, traversal succeeds, an unapproved action executes, or any unrestricted Hermes built-in becomes enabled.
