> Historical notes for the 9.0.0 encoding correction. The current candidate is 9.2.4; use [current setup](RESEARCH_PREVIEW_SETUP.md).

# Public Source Research Preview — Encoding Fix 1

Package v0.9.0.0 · Core Preview 9.0.0 · 28 August 2026

## Reported installation failure

The target-PC installer stopped in `test_research_worker.py`: Python 3.12 used the Windows
CP1252 default to read UTF-8 source files. The screenshot shows a UnicodeDecodeError on byte
0x9d at worker position 29825 and two errors among the 50 research tests. The gate stopped before
replacing the resident host; research installation was not completed.

The original research suite reproduced exactly two errors when Path.read_text defaulted to
CP1252: worker AST inspection at position 29825 and host source inspection at position 190634.
The source files were intact. The earlier Linux-only tests had missed this default-encoding difference.

## Correction

- Specify `encoding="utf-8"` on all six research-test source reads.
- Specify UTF-8 for the subprocess test's text protocol.
- Add a regression that reruns the actual host/worker source checks with CP1252 as the default
  for any source read that omits an encoding. It failed before the correction and passes afterward.

The worker, compiled-host source, Windows workflow implementation, installer logic, permissions,
model selection and approval/Stop behavior are unchanged. No tests are removed or skipped to
make installation proceed. No Windows locale setting or global Python environment change is needed.
The running core version therefore remains **9.0.0**; this is an installation-test correction.

## Verification

| Check | Result |
| --- | --- |
| Original research suite with CP1252-default source reads | Reproduced the two UnicodeDecodeErrors. |
| Corrected research suite, default-encoding warnings treated as errors | 51 passed. |
| Full corrected source suite | 274 discovered; 273 passed; one Windows compiler check skipped on Linux. |
| Full corrected source suite with CP1252-default Path.read_text | Same 273 passed and one Windows compiler skip. |
| Native Windows compile / owned-worker self-test | Still required by the installer; not executed in this Linux environment. |
| Live website + local Ollama research result | Still pending target-PC acceptance. |

The CP1252 check simulates the default used by the failing source reads; it is not a Windows
installation test or a claim that every Windows encoding/console behavior was exercised.

## Retry installation

Download the corrected ZIP again and extract it to a **new folder**. Its top-level folder is
`Cypher-9.0.0-EncodingFix1`. Run `INSTALL_CYPHER_RESEARCH_PREVIEW.cmd` normally, not as administrator.
Do not use the old extracted copy, skip tests, or change Windows language settings.

After a successful installer result, confirm Core Preview **9.0.0** and use the one-page test in
[RESEARCH_PREVIEW_SETUP.md](RESEARCH_PREVIEW_SETUP.md). Keep the accepted 8.5.3 package for rollback.

Python documents the locale-dependent default and recommends specifying an encoding for UTF-8
text. See [Python 3.12 text encoding](https://docs.python.org/3.12/library/io.html#text-encoding).
