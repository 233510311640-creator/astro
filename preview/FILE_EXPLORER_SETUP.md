Current bundle: **10.2.0 Bounded Office Documents**. Start with [OFFICE_DOCUMENTS_SETUP.md](OFFICE_DOCUMENTS_SETUP.md).
The component guide below is supplemental.

# Cypher 9.5.1 — File Explorer

Find files, browse subfolders and read small text files from Cypher. All three use the existing
folder grants, run without a model or network request, and leave file contents unchanged.

This patch corrects the Windows metadata comparison that blocked the 9.5.0 installer.
The failed install left the prior resident host unchanged. See RELEASE_NOTES_FILE_READ_COMPATIBILITY.md.

## Install

1. Keep the working 9.4.0 folder or ZIP for rollback. Finish any active task.
2. Extract this complete ZIP into a new folder.
3. Double-click **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally. Windows may hide `.cmd`.
4. Open Cypher with **Ctrl+Alt+Space** and confirm **CORE PREVIEW 9.5.1**.

The installer checks the new worker, including search, nested listing, reading and cancellation
against temporary fixtures, before replacing the resident host. Your existing folder grants remain.
No model download, new folder grant or performance benchmark is part of installation.

## One new file-reading check

Use your existing `desktop-demo` grant and send:

```text
Files: find desktop-demo "meeting"
```

The result should show the relative path of `meeting-notes.txt`, whether it is still loose or now
inside a subfolder. Then use the returned path in this command:

```text
Files: read desktop-demo "PATH-FROM-RESULT"
```

Replace `PATH-FROM-RESULT` with the returned path. For example, **only if the result shows it**:
`Files: read desktop-demo "Documents/meeting-notes.txt"`.
Send the final text-reading result screenshot. If the grant name differs, `Files: folders` shows
your current names. If a step fails, send that result; no repeat install or organization test.
Keep private file contents out of screenshots; the bundled meeting notes are a synthetic fixture.

## Commands

| Command | Result |
| --- | --- |
| `Files: folders` | Existing approved folders and their command names. |
| `Files: list desktop-demo` | Direct entries in the granted folder. |
| `Files: list desktop-demo "Documents"` | Direct entries in that subfolder. |
| `Files: find desktop-demo "meeting"` | Accessible files or folders with that literal fragment in their name. |
| `Files: find desktop-demo ".txt" in "Documents"` | Search starting inside a specified subfolder. |
| `Files: read desktop-demo "Documents/meeting-notes.txt"` | Small UTF-8 text, numbered lines and a digest of the bytes read. |
| `Files: status` | Existing file-change receipts and undo/review commands. |

Filename search is case-insensitive. It does not search file contents and does not interpret
wildcards, regular expressions or natural-language instructions. List is nonrecursive; find
searches the starting folder and up to four subfolder levels. Paths must stay inside the grant.

## Limits and meaning

Search/list inspect at most 1,000 directory entries, visit at most 50 folders, return at most 50
matches and check a three-second elapsed budget between operations. Reaching a limit produces
**PARTIAL**, with the reason. Matching results are sorted for display; enumeration order is supplied
by the filesystem, so limited searches are not a global alphabetical top 50. Protected/unavailable
entries are skipped and counted. A no-match result applies only to accessible entries scanned.
The timer is cooperative; an operating-system filesystem call can take longer before it returns.

Read accepts `.txt`, `.md`, `.csv`, `.json`, `.log`, `.rst`, `.yaml` and `.yml`, subject to existing
protected-name rules. Files must be valid UTF-8, at most 32 KiB, and free of NUL bytes. At most
200 lines are displayed; omitted lines produce PARTIAL. PDF, Office, binary, large-file and other
encoding support are not included. This is a text viewer, not a CSV/JSON renderer or AI summary.

File text appears as numbered data, with display controls escaped. Text stays in the current view;
it is not placed in model history or executed. Copy remains a separate human action. Stop discards
an unfinished result and waits for worker exit. Reading needs an existing `read_text` grant;
listing/search needs `metadata`. File modifications still require the existing exact plan approval.

See RELEASE_NOTES_FILE_EXPLORER.md and VALIDATION_FILE_EXPLORER.md. Runtime measurements remain
available, but this release changes no Ollama model, generation budget or runtime setting.
