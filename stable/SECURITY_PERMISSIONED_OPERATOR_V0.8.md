# Cypher v0.8 Permissioned Local Operator — Security Boundary

Status: Alpha 1; source tests passed, target-Windows acceptance still required.

## Authority model

The language model is a planner, not the security boundary. The Python broker resolves and validates
paths, checks capability scopes, binds proposals to file snapshots and a SHA-256 fingerprint, and
verifies filesystem postconditions. Human-side commands are intentionally absent from MCP.

The model can call only six new operator tools: permission status, bounded text read, proposal,
proposal retrieval, apply-after-approval and metadata-only operation status. It cannot add or remove
a permission, approve a proposal, invoke undo, select an administrator token, execute a shell or
permanently delete a file.

## Permission boundary

- Every root is an existing, explicit subfolder chosen by a person.
- Drive roots, the user-profile root, system folders, AppData, credential folders, hidden/system
  roots, links, junctions, reparse points and overlapping roots are rejected.
- Every path is relative to a registered root. Absolute paths, traversal, alternate data streams,
  Windows device names, deceptive trailing characters and link escapes are rejected.
- Capabilities are separately scoped: `read_text`, `create_text`, `replace_text`, `copy`, `move`,
  `rename`, `mkdir`, and `quarantine`.

## Approval and state

- Proposal does not change a user file.
- Approval is performed outside Hermes and binds the exact protected action list, path selection,
  content hash, source snapshot and expiry to one SHA-256 fingerprint.
- Plans and undo payloads are encrypted and authenticated with Windows current-user DPAPI.
- A reviewed proposal lasts 60 minutes. Approval opens a fresh 10-minute execution window.
- An approved plan can be claimed only once.

## Execution and recovery

- Create/copy/move/rename refuse overwrite.
- Replace uses an atomic temporary-file swap after the original snapshot is rechecked.
- Move and rename require same-filesystem atomic rename.
- Quarantine is reversible and can safely cross filesystems using copy, hash verification and source
  removal. It is not permanent delete.
- Every step writes a protected undo record before mutation, verifies its postcondition afterward,
  and enters a metadata-only journal state.
- A failure rolls back completed steps in reverse order. If rollback cannot safely prove the current
  state, the operation becomes `recovery_required` and MCP startup fails closed.
- Human undo refuses to overwrite or remove data that changed after execution.

## Privacy

Audit events contain operation type, success/failure class, plan/operation identifiers, counts and
byte totals. Operator errors do not copy raw exception messages into the audit. Prompts, answers,
content, filenames, requested paths, tool arguments, secrets and hidden reasoning are excluded.

The protected plan database necessarily contains encrypted paths, snapshots and replacement content
so an approved task can survive a restart. Anyone running as the same Windows user may be able to ask
DPAPI to decrypt that data; DPAPI does not protect against a fully compromised user session.

## Residual risks and limitations

- This is not a security sandbox against malicious software already running as the same Windows
  user.
- Metadata, file contents or instructions shown to a model remain untrusted evidence and cannot grant
  themselves authority, but a model may still propose a poor action. Human review remains required.
- File state can change between checks. Snapshot rechecks, exclusive creation, atomic rename and
  rollback reduce this time-of-check/time-of-use risk but cannot remove all filesystem races.
- Network shares and unusual filesystems may not provide the same durability or rename semantics as a
  local NTFS volume; they are not acceptance-tested in Alpha 1.
- Directory moves/copies, ACL editing, shortcuts, executables, registry, services, processes, UI
  Automation, browser actions and permanent deletion are not supported.
- The production DPAPI path and PowerShell integration must still pass tests on the target Windows 11
  PC. Passing tests in the build environment are not a substitute for that validation.
