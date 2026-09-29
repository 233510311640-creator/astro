# 9.4.0 validation record

Linux / Python 3.12, 10 September 2026.

| Gate | Result |
| --- | --- |
| Full regression, EncodingWarning treated as error | 478 discovered; 477 passed; one native Windows compiler test skipped. |
| New runtime behavior tests | 24 passed, including fixed-loopback transport, no-generation status, exact one-call benchmark, cloud/missing-model guards, malformed metrics, cancellation and actual isolated entrypoint. |
| Existing file tests | Retained; receipt assertions now also verify reversed-step counts and no filename/content disclosure in metadata status. |
| Preserved source components | Eleven file-engine, native file-host, research and workflow source files byte-compared against 9.3.0: identical. |
| Worker integrity | File ZIP matches bundled source and its pin; standalone runtime worker matches its separate compiled-host pin. |
| Syntax and launcher format | Python source compilation passed; current installer CMD files retain CRLF. |
| Fresh extraction | Every packaged manifest entry checked; full regression rerun from extracted ZIP with the same result. |

The installed native host will compile and run its WPF layout/command checks, workflow checks,
owned file/DPAPI fixture, research boundary fixture and new offline runtime-worker fixture before
replacement. Runtime fixture mode uses synthetic metadata and makes no live HTTP/model request.

Windows compilation, Windows jobs, WPF layout, live Ollama metrics and target GPU residency are not
claimed as executed in Linux. Source checks and test doubles are not substitutes for those results.
The user's 9.3.0 screenshots establish only the live file scenarios recorded in the release notes.

The next target-PC gate is one `Runtime: status` followed, if local weights are present, by one
`Runtime: benchmark`. No repeated file or academic acceptance capture is requested. Preserve any
actual error/status as evidence before considering another release.
