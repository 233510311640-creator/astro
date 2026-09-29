# Cypher 9.5.1 — Windows text-read compatibility

15 September 2026. Core Preview 9.5.1; Python distribution 0.9.5a2.

The 9.5.0 installer failed its temporary text-read fixture at `file_browser.py` line 117.
The screenshot confirms that the installer stopped before replacing the resident host. It does
not report which individual metadata field differed, so no exact target-PC field is claimed here.

## Correction

9.5.0 compared a path-based `stat` snapshot directly with a handle-based `fstat` snapshot,
including creation/change and modification timestamps. That unnecessarily required both APIs
to return identical timestamp representations as well as the same underlying file.

9.5.1 compares full path snapshots before/after the read, and full handle snapshots before/after
the read, separately. It still compares device/file identity across the APIs and requires the
actual byte count to equal every observed size. No timestamps are rounded or discarded. Every
comparison remains exact within its API. Distinct failure messages identify path, handle, identity
or size disagreement if a future read fails, without printing file contents or raw metadata.

Python documents that stat timestamp meaning and resolution depend on the operating system and
filesystem, and that Windows creation/change-time semantics are evolving.
[Python stat result documentation](https://docs.python.org/3/library/os.html#os.stat_result).

## Evidence and retained behavior

- The new stable-but-different path/handle timestamp fixture fails against unmodified 9.5.0 at
  the same rejection line shown by the user, then passes against 9.5.1. This models the comparison
  defect; it is not a measurement of the target PC's timestamps.
- Additional tests prove changes within either snapshot stream still fail, as do identity and
  size disagreements. Existing growth, permission revocation, binary/encoding, limits and Stop
  tests remain passing.
- All 23 browser tests pass. Full portable suite: 501 discovered, 500 passed, one Windows-only
  compiler test skipped. Fresh archive extraction reruns the suite and verifies all checksums.
- The native installer still runs the full file fixture before replacing the installed host.
  No gate was removed or bypassed; search, listing, text-read, organization, undo and cancellation
  fixtures remain in that check.
- Search, grants, file modification/undo, native file-host behavior, research, runtime/model
  settings and Windows workflows are unchanged. Only the reader comparison, its tests, version
  surfaces, package pin and release guidance change.

The 32 KiB actual-read cap, UTF-8 restrictions, protected paths, no-model/no-network behavior and
exclusion of file text from model history remain. Existing same-user filesystem trust assumptions
apply; this is not a claim of OS-level containment or prevention of all adversarial races.

## Install

Keep the prior working 9.4.0 package for rollback. Extract the complete 9.5.1 ZIP into a new folder
and run **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally. Confirm **CORE PREVIEW 9.5.1**.
There is no need to uninstall, change permissions, run a separate checker or repeat 9.5.0.
If the installer reports another failure, preserve its result; do not bypass its checks.

After installation, FILE_EXPLORER_SETUP.md contains the one find/read check. Native Windows
compilation, DPAPI and live UI execution remain target-PC checks, not claimed as run in Linux.
