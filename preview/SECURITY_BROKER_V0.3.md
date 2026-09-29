# v0.3.3 security boundary and limitations

## Enforced

- One fixed existing sandbox root.
- Direct operations are limited to bounded listing and small UTF-8 text reads.
- File mutations begin as immutable, SHA-256-fingerprinted plans with a 60-minute human-review expiry.
- No proposal changes the filesystem.
- Approval is available only through the separate human-side CLI; it is not an MCP tool.
- Approval is bound to the exact plan ID, root, action, payload, and expiry.
- Approval creates a fresh 10-minute execution window without changing the fingerprinted action.
- Apply is single-use and rejects unapproved, expired, failed, executed, or wrong-root plans.
- Existing targets are never overwritten by create, move, or folder operations.
- Text replacement rechecks the original SHA-256 immediately before execution.
- Undo is human-side, type-confirmed, and refuses to overwrite later changes.
- Paths, protected names, hidden/system objects, links, junctions/reparse points, sizes, and file types are validated.
- A failed state commit triggers filesystem rollback.

## Absent

- No deletion proposal, shell, process, code execution, web, browser, UI control, credentials, messaging, scheduling, administrator access, or access outside the sandbox.
- No MCP sampling or elicitation is needed; both remain disabled.
- No third-party Python dependency or network client code.

## Privacy and remaining risks

- Proposed text and reversible pre-edit snapshots are stored locally in `%LOCALAPPDATA%\LocalAssistantBroker\action_state.db`. Do not use this sandbox for sensitive material during development.
- File contents can contain prompt injection. Content is data and never grants permission.
- Another malicious process already running as the same Windows user could race or alter local files. This broker is an assistant authorization boundary, not an antivirus or OS sandbox.
- BitLocker protects powered-off data; it does not isolate an unlocked Windows session.

Remove the integration immediately if an unexpected tool appears, an unapproved plan executes, a boundary test reads outside the sandbox, or a raw Hermes computer tool becomes enabled.
