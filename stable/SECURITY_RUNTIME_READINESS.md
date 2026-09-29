# Runtime diagnostics boundary — 9.4.0

Native human input alone dispatches `Runtime:`. Runtime commands are not model/MCP tools and
cannot be dispatched by a generated response or research evidence. UI shortcuts fill input only.
Auto/Fast and Deep select their configured model roles explicitly; no fallback is introduced.

The standalone worker is SHA-256 pinned separately from the file worker. The existing owned
process client launches isolated Python with a minimal environment and an owned one-process,
512 MiB Windows job before sending input. Runtime protocol requires input, selected model and a
fresh nonce. The parent rejects review/progress/action frames in runtime mode and accepts success
only after bounded, nonce-bound final output and confirmed worker exit. No file-task functions
are imported by the runtime worker; no runtime functions are included in the file-worker ZIP.

HTTP is limited in code to `127.0.0.1:11434`: GET version/tags/ps, and POST show/generate. No proxy,
redirect, authentication, remote URL, model pull, unload, shell, file read/write, registry change,
model tool, user conversation or generated-text export is used. Status performs no generation.
Benchmark requires a selected installed local GGUF record plus local architecture metadata and
absence of remote alias flags before the one synthetic prompt. This trusts the installed local
Ollama service and is not an OS network sandbox or protection against arbitrary same-user tampering.

Connect timeout is at most two seconds. Status has a 15-second total budget; benchmark has a
90-second total budget. Metadata body caps are 256 KiB, except show at 1 MiB. JSON object keys must
be unique; names, counts, durations, content type, model identity and completion are validated.
Only bounded model identifiers and numeric metrics enter the report. Generation/thinking text and
context do not. Timing is reported as measured; GPU figures are residency snapshots, not peaks.

Stop sets cancellation, shuts down the active client socket, suppresses later requests and waits
for owned-worker exit. A submitted Ollama generation may continue server-side. Shared-server
termination, unloading, retry and model replacement are deliberately absent. The existing parent
watchdog remains a last-resort process ownership boundary, with no claimed successful measurement
on an unverified exit. Reports stay in the current native view; Copy is a separate human action.

The file engine, native file approval host, research and Windows workflow authority remain as in
9.3.0. File status reads the existing journal and labels reversal separately from historical forward
verification. It does not replay, approve, undo or modify a task.
