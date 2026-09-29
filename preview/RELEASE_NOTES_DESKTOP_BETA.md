# Cypher v0.9.3.0 — Everyday Desktop Beta

10 September 2026. Python distribution 0.9.3a1; native Core Preview 9.3.0.

Previously, a file plan's approval required leaving Cypher for a separate human-side command-line
tool. This release connects the existing permissioned operator directly to the native approval
panel. The same interface now handles local file tasks and the already implemented registered-app
workflows. This is one desktop integration bundle; academic expansion remains paused.

- Adds deterministic `Files:` commands for folder permissions, bounded organization, mkdir,
  move/copy, text creation/replacement, proposal review, status, undo and recovery.
- Displays complete source/destination paths and full replacement text before approval. The
  native panel sends the exact fingerprint over its private stdin connection; no approval tool
  is exposed to a model. Folder grants explicitly disclose that they persist.
- Lets an approved organization batch create its category folders before its moves. Every future
  destination is tied to an earlier approved mkdir; all existing path and collision checks remain.
- Adds cooperative Stop checks between file actions, verified rollback, single-use cancelled
  plans and a nonblocking execution lease shared by updated native and broker code.
- Keeps new tasks blocked until the owned file worker exits. Unknown exits, interrupted changes
  and failed reversals retain recovery evidence; forward actions are never replayed.
- Packages the standard-library file worker in a deterministic ZIP application, pins its complete
  SHA-256 in the compiled host, and starts isolated Python under an owned Windows job with a
  one-process and 512 MiB ceiling. A 180-second soft deadline requests Stop; at 210 seconds an
  unresponsive owned worker can be terminated and requires recovery inspection, never a claimed
  successful rollback. Normal Stop is cooperative, with no countdown or artificial wait.
- Reuses the established dark native layout. The third starter now opens file-command help.
  Full plans appear in the scrollable conversation area, with approval buttons kept visible.
- Adds a pre-replacement native file check for DPAPI, organization, undo and Stop on disposable
  fixtures. The included Desktop-Demo folder and setup guide consolidate the live Windows checks.

No Computer Use plugin, new framework, paid service, model download, model substitution or new
research request is used. File tasks use zero generations. Windows app workflow engine sources,
ResearchHost.cs and research_worker.py remain byte-identical to 9.2.12.

## Validation

See `VALIDATION_DESKTOP_BETA.md` for the final source/archive results. Native Windows execution
is pending on the target PC. The installer preserves the required native gates before replacement;
portable tests are not a substitute for WPF, DPAPI or real UI Automation results.

## Limits

This is a bounded desktop beta, not unrestricted computer control or general file understanding.
Organization uses file extensions and does not read document meaning. File operations allow
16 MiB per file, 128 MiB per task and 50 actions; organization considers at most 200 direct entries.
The existing app workflow limit is six steps across three registered apps. App text delivery has
no automatic save/undo. Separate file and app plans are not a single cross-system transaction.

Worker ownership, isolated imports, integrity pins and job restrictions do not provide OS-level
filesystem/network containment. The trusted file worker enforces approved roots in application
code. Another older broker process does not participate in the new execution lease; snapshots and
collision checks still reject detected external changes. Do not run competing file operations.
Research containment, coverage and runtime measurements remain tracked future work.

Keep the successfully installed 9.2.12 package for reinstall rollback. Complete or recover file
operations before rollback; do not erase the existing operator journal or its protected undo data.
