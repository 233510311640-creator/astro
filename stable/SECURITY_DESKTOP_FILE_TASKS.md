# Native file-task boundary — 9.3.0

Only typed native `Files:` input reaches this worker. Chat/model/research output never invokes it.
The standalone broker still cannot mint human approval. The native host shows the full proposal,
then sends one approve/deny decision bound to the plan fingerprint and a fresh 128-bit request
nonce over a redirected private stdin pipe. Responses have strict schemas, frame/count limits
and nonce binding; success is displayed only after a valid final result and confirmed zero exit.
Review expires after 120 seconds. EOF, malformed controls, denial and Stop cancel forward work.

Python starts with `-I -S -B -X utf8` against the integrity-pinned file_operator.pyz, using only the
standard library and bundled modules. It receives a minimal environment, no shell and no model
tools. The host assigns an owned job before sending input; one active process, 512 MiB memory and
kill-on-host-exit apply. These job limits are ownership/resource controls, not AppContainer or a
filesystem/network sandbox. File paths are confined by the existing broker policy checks.

The native folder picker selects one existing directory. A separate exact review adds its lasting
capabilities to the same human-managed operator allowlist. Full drives/profiles, protected
directories, overlaps, links and reparse points remain refused. `Files: remove ROOT` removes the
grant after review without deleting files. It refuses removal while recovery is outstanding.
Every subsequent file plan still needs a fresh approval. Permissions reload before execution;
root bindings, file snapshots, destinations and postconditions are revalidated by the operator.

Plans and undo data stay protected by the existing current-user Windows DPAPI implementation.
SQLite transactions persist step preparation before execution and retain verification receipts.
The updated operator uses a nonblocking per-journal OS file lease across apply, undo and recovery.
An older broker executable does not share that lease; this is not protection against arbitrary
same-user software. Paths and file contents are never sent to Hermes or added to research/chat
history by this route. Metadata and encrypted undo payloads remain in LocalAssistantBroker.

Stop checks run between forward file steps, followed by reverse verification. A Stop before the
first action still retires the claimed plan. Undo/recovery cancellation leaves a reviewable
remainder. A reversal never overwrites a later external edit to claim success. Unfinished journal
entries block new file changes until reviewed recovery succeeds; restart does not replay actions.
New host requests remain disabled until the owned worker exit is confirmed. If the hard deadline
or a broken transport terminates it, the UI reports recovery required rather than claiming rollback.

The installer runs native DPAPI/file fixtures in a fresh temporary tree with a fixture-only
allowlist and protector; it never edits user folder grants during tests. Portable tests inject a
test protector. Production uses Windows DPAPI only. The temporary fixture is bounded to files
created by that check. It does not claim to verify real document content, UI Automation or full
OS isolation. The source and research boundary are documented separately.
