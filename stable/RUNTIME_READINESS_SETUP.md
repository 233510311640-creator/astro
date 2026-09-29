Current bundle: **10.2.0 Bounded Office Documents**. Start with [OFFICE_DOCUMENTS_SETUP.md](OFFICE_DOCUMENTS_SETUP.md).
The component guide below is supplemental.

Current bundle: **9.5.0 File Explorer**. Start with [FILE_EXPLORER_SETUP.md](FILE_EXPLORER_SETUP.md).
The component guidance below is historical or supplemental.

# Cypher 9.4.0 — Runtime Readiness

This bundle adds local runtime status, one short selected-model performance check and clearer
file-task receipts. It reuses the existing dark interface and preserves the verified file engine.

## Install

1. Keep your working **9.3.0** folder or ZIP for reinstall rollback. Finish any active request.
2. Extract this complete ZIP into a fresh folder.
3. Run **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally. Windows may hide the `.cmd` extension.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.4.0**.

The familiar launcher installs the complete bundle. Native layout, workflow, file and research
checks remain before replacement. A new owned-runtime-worker check uses offline fixtures only;
the installer does not run a model performance test, alter model files or add folder permissions.

## One Windows check

Keep **Auto** selected and send this in Cypher:

```text
Runtime: status
```

The new **System status** button also fills that command; press Send afterward. Expect a report
showing whether Ollama is reachable, whether the selected model is installed, and whether it is
currently loaded. **Not observed in loaded models** is normal when an installed model is idle.
This status request does not load a model or generate an answer.

If status finds the selected local model, send:

```text
Runtime: benchmark
```

This performs one short synthetic generation and shows server total time, loading time, prompt
evaluation time, output speed and a GPU-memory residency snapshot. Send its final result screenshot.
If status or benchmark fails, send that result instead; do not reinstall or repeat the same check.

Your previous folder permission, organization, verified undo and cancellation-before-approval
checks are already recorded. **Do not repeat them for this release.** The **File tasks** button
fills `Files: status` if you want to inspect the clearer receipts; it makes no file changes.

## What the measurements mean

| Field | Meaning |
| --- | --- |
| Installation | The selected name was found in local model metadata. Missing/unverified weights prevent a benchmark. |
| Residency before | Whether the model appeared in Ollama's loaded-model list before the test. |
| Client generation request | Elapsed time around the single generation HTTP request. |
| Server total | Ollama's reported total duration for that generation, converted from nanoseconds. |
| Model loading | Ollama's reported loading duration for that request. |
| Prompt evaluation | Ollama's reported prompt-processing duration. |
| Output speed | Reported output-token count divided by reported generation duration. |
| Reported GPU memory | `size_vram` for that model, converted to GiB; a residency snapshot. |
| Finished at token budget | The short test reached its 64-token ceiling; this is disclosed, not treated as an answer-quality pass. |

These are not peak VRAM, whole-GPU utilization, a controlled cold/warm comparison or evidence of
answer quality. Other local software can affect the readings. The benchmark can load the selected
model and resize its context to 4,096 tokens. It does not force an unload, change configured model
roles, download weights or perform a second generation. Thinking and keep-alive use server defaults.

Auto/Fast uses the configured Fast model; selecting Deep explicitly measures the configured Deep
model. No fallback model is substituted. The benchmark first verifies local GGUF metadata and
model information and rejects cloud/remote aliases. Only the fixed synthetic prompt is submitted.
No conversation, document, file contents, generated response or thinking text is saved in the report.

## Failure and Stop

- `OLLAMA_CONNECTION_FAILED`: the local server could not be reached. Reopening Cypher uses its
  existing pinned Ollama startup path. This report alone does not indicate an installation defect.
- `SELECTED_MODEL_NOT_INSTALLED`: the configured selected model was absent; no generation ran.
- `LOCAL_MODEL_NOT_VERIFIED`: a remote alias or missing local-weight information blocked generation.
- `OLLAMA_HTTP_..._AT_...`: the exact status and local endpoint that rejected the request.
- `RUNTIME_TIME_LIMIT`: the bounded local request did not finish. No retry ran.
- `GENERATION_RESPONSE_INVALID` / `GENERATION_METRICS_INVALID`: returned completion or timing data
  did not pass validation. No successful measurement is claimed.
- `PARTIAL`: some status information or the after-generation residency snapshot is unavailable.
  Valid generation metrics, if already received, are retained and clearly separated.

Stop closes the check's connection and prevents further requests. It waits for the owned worker
to exit before accepting another task. A generation already submitted to the shared Ollama server
may still finish there; Cypher does not claim that its server-side computation was terminated.

Reports stay in the current view. Copy is available if you want to share the result yourself.
No automatic export, background polling, scheduled benchmark or new provider is added.
