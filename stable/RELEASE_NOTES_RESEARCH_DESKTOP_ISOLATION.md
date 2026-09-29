# Core Preview 9.0.6 — fail-closed research desktop isolation

Package v0.9.0.6 · Python package 0.9.0a7 · 1 September 2026

## Starting evidence

The user's 9.0.5 target result accepted the preceding fail-closed scope guard: the local draft added
unsupported wording, so Cypher displayed `CLAIM_SCOPE_UNSUPPORTED`, retained both source records and
displayed zero findings. No accepted Windows workflow behavior needs another regression run.

The research worker already had a fixed hashed script, isolated Python flags, cleared environment,
one-process job, 512 MiB process-memory limit, host-owned lifetime and no action tools. It still ran
under the signed-in user's token and its job did not restrict access to Windows desktop surfaces.

## Changes

- Before starting the worker, set every documented `JOBOBJECT_BASIC_UI_RESTRICTIONS` flag used by
  this preview: `HANDLES`, `READCLIPBOARD`, `WRITECLIPBOARD`, `SYSTEMPARAMETERS`, `DISPLAYSETTINGS`,
  `GLOBALATOMS`, `DESKTOP` and `EXITWINDOWS`.
- Query the job object immediately and require an exact mask match. Any set failure, query failure or
  weakened returned value fails closed as `WORKER_UI_ISOLATION_UNAVAILABLE` before `Process.Start`.
- Keep assignment to the same one-process, kill-on-close, memory-bounded job before the host writes
  request JSON to stdin.
- Exercise this setup in the installer's native offline self-test. Installation does not replace the
  resident host unless the job limits and desktop restriction mask are accepted by Windows.

The Windows job restrictions block clipboard reads and writes; use of USER handles and hooks owned by
other processes; desktop creation/switching; display/system-parameter changes; Windows exit calls;
and global-atom sharing. The worker needs none of those surfaces for bounded HTTPS reading or its
loopback Ollama call.

## Deliberate limits

This is compatible job-level desktop hardening, not AppContainer. The worker still has the signed-in
standard user's token. Filesystem, registry and network isolation are not newly enforced by the OS;
the existing deterministic reader policy remains the network boundary. Same-user Python/runtime or
host tampering remains outside this preview's guarantee.

Microsoft's newer `Experimental_CreateProcessInSandbox` API was not adopted because it is explicitly
experimental and requires a compiled sandbox specification. AppContainer/LPAC or another stable
filesystem/network boundary remains a separately tested future milestone.

No search provider, page/model retry, additional local-model call, model download, approval, arming
delay, Stop stage, app/file permission or Windows workflow change is introduced.

## Verification

- 347 Python tests discovered: 346 passed and one Windows-only compiler test skipped.
- All 124 research tests pass. The new regression requires the eight exact restriction constants,
  set/read-back verification, fail-closed diagnostic, ordering before worker start, and absence of a
  `UserHandleGrantAccess` escape.
- Full-suite source reads pass with the default encoding forced to Windows CP1252.
- The research suite passes with `EncodingWarning` treated as an error.
- Existing Windows workflow sources are byte-identical to 9.0.5.
- Research worker behavior changes only its version/header text; the pinned SHA-256 is updated.
- Native compilation and the real job-object self-test remain target-Windows installer gates.

## Target-PC acceptance

Keep 9.0.5 for rollback. Extract 9.0.6 into a new folder and run
`INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, not as administrator. A successful installer result
and **CORE PREVIEW 9.0.6** heading accept this slice. No live website, model, workflow, approval or
Stop-race retest is required.

## Primary implementation references

- Microsoft, [JOBOBJECT_BASIC_UI_RESTRICTIONS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_ui_restrictions)
- Microsoft, [SetInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject)
- Microsoft, [Create Process In Sandbox APIs](https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox) (experimental comparison only)
