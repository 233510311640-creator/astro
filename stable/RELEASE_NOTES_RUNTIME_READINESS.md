# Cypher v0.9.4.0 — Runtime Readiness

10 September 2026. Native Core Preview 9.4.0; Python distribution 0.9.4a1.

The user has verified 9.3.0 folder granting, four-action organization, verified undo and cancellation
before approval on Windows. This release preserves that file engine and makes local runtime
diagnosis and file-task receipts accessible from the same workspace.

## Changes

- Adds **System status** and **File tasks** header buttons. Each fills its explicit command;
  Send starts it. The buttons are disabled during active work and participate in native layout checks.
- `Runtime: status` performs three bounded metadata reads against fixed local Ollama endpoints.
  It reports installed-model and loaded-model state separately, with no generation or model load.
- `Runtime: benchmark` validates the selected model's local weights and makes one synthetic
  generation: 4,096 context tokens, 64 output tokens, zero temperature. Thinking and keep-alive
  remain server defaults. It never retries, substitutes a model, pulls weights or forces unloading.
- Reports client request time, server generation/loading/prompt durations, output speed and
  before/after residency snapshots. Token-budget completion is disclosed. Generated text,
  thinking and context are never put in the report or saved by this worker.
- Rejects remote/cloud aliases, missing weights, invalid metrics, uncompleted generations,
  mismatched models, redirects, duplicate JSON keys, oversized bodies and unexpected result schemas.
- Uses a separately pinned standalone Python runtime worker through the existing owned-process
  client. Runtime mode accepts terminal results only; it cannot request a file/action approval.
  File and runtime binaries have independent pins; the file ZIP does not include runtime code.
- File receipts now show readable states, action counts, UTC creation time, forward verification
  receipts, reversed-step counts and exact undo/review commands. No new action execution is added.
- The installer validates all new source/binary pins and runs an offline native runtime-worker
  fixture before stopping/replacing the installed host. No model benchmark runs during installation.

## Verified continuity

The file operator engine, capability broker, permission center, DPAPI protector, native FileTaskHost,
research worker/bridge and all four Windows workflow files are byte-identical to 9.3.0. The file
worker changes only its receipt renderer and component version; its package pin is synchronized.
The shared owned-process client adds a distinct runtime mode without changing default file mode.

9.3.0's target-PC screenshots confirm organization and undo for operation
`ec09e5a0-d335-455a-a715-5629e27af643` and a later cancellation with no file action. They do not prove
Stop during an in-flight native operation or a new 9.3 editor regression run. Earlier accepted app
workflow behavior is retained; those scenarios are not relabelled as newly executed here.

## Measurement limits and API contract

Ollama documents `size_vram` in its loaded-model response. Cypher labels it a model-residency
snapshot, not peak/whole-device memory. [Running models API](https://docs.ollama.com/api/ps).
Generation durations are documented in nanoseconds; output speed is calculated from output count
and generation duration. [Generate API](https://docs.ollama.com/api/generate).
Installed names are obtained from [the model-list API](https://docs.ollama.com/api/tags).
Remote-alias flags and local model information are checked against the official
[Ollama API types](https://github.com/ollama/ollama/blob/main/api/types.go).

A model absent from the initial loaded list is not proof of a controlled cold start. A model already
loaded may still resize/reload for this test. No average, peak, causal performance improvement or
answer-quality score is inferred from one short generation. Cold/warm comparisons and continuous
resource measurements remain future work driven by these first target-PC readings.

Stop terminates the client check, not necessarily an already-submitted shared-server generation.
The worker uses fixed loopback only and no proxy/redirect, but it is not OS-level filesystem or
network containment. No Computer Use plugin, public research request, cloud inference, paid service,
new framework, background polling, scheduled job, model download or approval countdown is added.

See RUNTIME_READINESS_SETUP.md for the single Windows handoff and VALIDATION_RUNTIME_READINESS.md
for portable verification. Native execution of this new release remains pending on the target PC.
