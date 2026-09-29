# 9.5.1 validation record

Portable verification: Linux / Python, 15 September 2026.

| Gate | Result |
| --- | --- |
| Full suite, EncodingWarning treated as error | 501 discovered; 500 passed; one Windows-only compiler test skipped. |
| New browser tests | 23 passed. Includes a regression that fails against 9.5.0 when path and handle timestamps differ, plus rejection of real per-API changes, size mismatch and file-identity mismatch. Real temporary files cover search without content opens, scoped/nested listing, Unicode/BOM, byte digest, empty files, line truncation, protected paths, revoked/narrowed grants, scan budgets, Stop, growth during read, binary/encoding/size rejection, literal matching and response size. |
| Packaged file-worker fixture | Isolated Python ZIP import runs the extended full file fixture, now including browse/find/read/Stop. |
| Worker pins | File worker source/package/native pin aligned; independent runtime and research workers unchanged. |
| Native installation order | Existing compilation, layout, workflow and offline worker checks remain before resident-host replacement. |
| Fresh archive extraction | All packaged checksums verified; same full suite rerun from the extracted ZIP. |

Native Windows compilation, WPF, Windows jobs, DPAPI and live UI execution are not claimed as run
on Linux. Windows executes the native installer fixtures. A link fixture is created where permitted;
standard-user Windows may prohibit creating it, in which case inaccessible-link reads are still rejected.

The remaining target-PC check is find a known synthetic note inside an existing grant, then read
the returned path. No model benchmark or repeated file modification test is requested.
