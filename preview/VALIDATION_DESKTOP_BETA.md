# 9.3.0 desktop beta validation

Build environment: Linux, Python 3.12. Validation date: 10 September 2026.

| Gate | Result |
| --- | --- |
| Complete regression suite | 454 discovered; 453 passed; one native Windows compiler test skipped on Linux. |
| Same suite with EncodingWarning treated as an error | 453 passed; the same Windows-only skip. |
| New file-task and package tests | 25 passed, including organization/undo, stopped apply, stopped undo with reviewed recovery, collisions, source changes, permission revocation, shared execution lease, expired review and private protocol approval. |
| Isolated packaged imports | The actual bundled modules complete their disposable file fixture under Python `-I -S -B -X utf8`, using the portable test protector. |
| Production entrypoint on Linux | Actual isolated ZIP entrypoint imports successfully and rejects unavailable Windows DPAPI without exposing a traceback. This is not a Windows DPAPI pass. |
| Source integrity | Whole file-worker ZIP hash matches the compiled-host pin; bundled modules match source bytes. |
| Preserved components | Research worker, ResearchHost.cs and four Windows workflow source files byte-compared against 9.2.12: all identical. |
| Python syntax and Windows launchers | Source compilation checks passed; current installer launchers retain CRLF. |
| Fresh ZIP extraction | Every manifest entry checked; full suite rerun from extraction with the same result. |

The new tests exercise observable behavior and boundary failures, not only source/version strings.
The 203 retained research tests include the existing simulated CP1252 source-read check.

## Required Windows gates

The .NET/WPF compiler, Windows job APIs, Windows DPAPI and real editor UI Automation are unavailable
in this Linux environment. They are not claimed as executed here. The installer performs native
compilation and host/layout/workflow/research self-tests before replacing the running host. It also
executes `--file-self-test` under the owned worker with actual DPAPI and private temporary file fixtures.
On Windows, the Linux-only DPAPI-refusal test is skipped and the native workflow compiler test runs.

Follow DESKTOP_BETA_SETUP.md once after installation for actual native approval, organization and
undo, the registered editor workflow, and cancellation. The installer fixture proves engine behavior
on Windows; those manual checks establish the live UI integration. A successful 9.2.12 installation
is the user-reported baseline and does not substitute for these new 9.3.0 results.

## Remaining limits

No claim of general computer autonomy, OS-level file-worker containment, arbitrary application
support, semantic file organization, academic coverage improvement, cold-start latency or VRAM
measurement is made. App text delivery has no automatic file save or undo. File undo refuses
conflicting external edits and requires reviewed recovery when verification cannot finish.
