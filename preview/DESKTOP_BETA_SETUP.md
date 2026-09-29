Current bundle: **10.2.0 Bounded Office Documents**. Start with [OFFICE_DOCUMENTS_SETUP.md](OFFICE_DOCUMENTS_SETUP.md).
The component guide below is supplemental.

Current bundle: **9.5.0 File Explorer**. Start with [FILE_EXPLORER_SETUP.md](FILE_EXPLORER_SETUP.md).
The component guidance below is historical or supplemental.

Current 9.4.0 release: see RUNTIME_READINESS_SETUP.md and SECURITY_RUNTIME_READINESS.md. Previously verified file tests do not need repeating. Historical component documentation follows.

# Cypher 9.3.0 — Everyday Desktop Beta

This release brings the existing file operator into Cypher's native task and approval flow.
The graphite/violet workspace now has an **Organize files** starter. It fills a command; Send
starts the request. File tasks use no model or network request.

## Install once

1. Keep the working **9.2.12** folder or ZIP for reinstall rollback. Finish any active task.
2. Extract this entire ZIP into a fresh folder.
3. Double-click **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally. Windows may hide `.cmd`.
   The familiar launcher now installs the complete desktop bundle.
4. Wait for the success message, then press **Ctrl+Alt+Space**. Confirm **CORE PREVIEW 9.3.0**.

The installer checks the complete host, WPF layout, workflow engine and research boundary. It also
runs the new owned file worker against temporary files, testing real Windows DPAPI, organization,
verified undo and Stop rollback **before replacing the installed executable**. It does not grant
permission to a user folder. If a check fails, send the error; no repeated research test is needed.

## One acceptance session

Use the supplied **Desktop-Demo** folder, which contains only two disposable sample files.
All commands below go into Cypher's message box. Review each consequential task and use its
existing **Approve once** button.

### 1. Organize and undo

Send `Files: add folder`, select **Desktop-Demo** inside this extracted package, and approve that
folder permission. Cypher displays its command name, normally `desktop-demo`. If that name was
already taken, use the exact new name Cypher displays.

Send:

```text
Files: organize desktop-demo
```

The plan should show four actions: create Documents and Spreadsheets, then move the two samples
into those folders. Approve once. Expect **4 file actions verified** and an undo option.

Then send:

```text
Files: undo last
```

Review and approve. Expect **File task undone and reverse changes verified**. The original
`meeting-notes.txt` and `budget.csv` should be back directly inside Desktop-Demo, and the two
new category folders should be gone.

### 2. Check the existing registered editor workflow

Use one blank, disposable Notepad document. Its existing Cypher app registration and text-entry
permission must already be enabled. Avoid other Notepad windows or dialogs during this check.
Send this as one multiline request (Shift+Enter inserts a newline):

```text
Workflow:
Open Notepad and write: Cypher desktop beta check.
Minimize Notepad
```

Review and approve. Expect **3/3 verified steps** and a minimized Notepad window. Restore it
manually and confirm the supplied text. This existing workflow verifies text delivery; it does
not save a document or offer file undo. A permission refusal is a refusal, not a pass.

### 3. Check cancellation from the shared task interface

Send `Files: organize desktop-demo` again. When the review appears, click **Stop** before approval.
Expect **CANCELLED**, with both sample files still in their original locations. Send `Files: status`
to see the earlier undone operation and the denied/cancelled proposal. A cancelled task is never
automatically replayed after restart. The installer separately exercises Stop after a file step
and verifies rollback using its own temporary fixtures.

Report the outcome of these three checks together. Include an error/result screenshot only if a
check fails. You do not need to repeat the academic research diagnostic.

## Commands for everyday use

`ROOT` means the approved folder name shown by `Files: folders`, not a drive or arbitrary path.
Paths are relative to that folder. Put double quotes around paths with spaces.

| Request | Result |
| --- | --- |
| `Files: help` | Show supported commands. |
| `Files: add folder` | Choose and review one lasting folder permission. |
| `Files: folders` | Show currently approved folders and capabilities. |
| `Files: remove ROOT` | Review removing a folder permission; leave files in place. |
| `Files: list ROOT` | List bounded direct entries; no content read. |
| `Files: organize ROOT` | Review grouping recognized loose files by file type. |
| `Files: mkdir ROOT "Drafts"` | Review creating one folder. |
| `Files: move ROOT "note.txt" to ROOT "Drafts/note.txt"` | Review an exact move into an existing folder. |
| `Files: copy ROOT "note.txt" to ROOT "Drafts/note.txt"` | Review an exact copy. |
| `Files: create ROOT "note.txt" : your text` | Review a new small UTF-8 text file. |
| `Files: replace ROOT "note.txt" : replacement text` | Review the entire replacement; retain protected undo data. |
| `Files: review PLAN-ID` | Review an existing unapproved file broker proposal in the native panel. |
| `Files: status` | Show recent local plan states, verified receipts and undo availability. |
| `Files: undo last` | Review reversing the latest completed file task. |
| `Files: recover` | Review remaining reversal after an interrupted task; never replay forward actions. |

Organization scans at most 200 direct entries and plans at most 50 actions, including new folders.
It permits up to 16 MiB per file and 128 MiB per task, skips unrecognized types and does not recurse.
Existing destination files cause rejection. Moves must remain on one filesystem; copy supports
another approved root. Symlinks, junctions, protected areas and out-of-root paths remain blocked.

Stop is cooperative between file steps. It lets the current bounded step return, then reverses
performed forward changes. If an external edit prevents safe reversal, Cypher reports **RECOVERY
REQUIRED** and blocks further file changes. Stop during undo/recovery pauses that reversal; review
`Files: recover` to continue. It never overwrites an external edit to manufacture a success result.

Folder grants persist until removed. Removing a grant can prevent undo until the same root is
restored. Plans/undo payloads use current-user DPAPI; task metadata stays in the existing local
operator journal. File task content is not sent to Hermes, Ollama or research providers.

## Validation boundary

9.2.12 is the user-reported installed baseline. The research worker and its native bridge, plus
the four workflow source files, are byte-identical to that package. The 9.3 host routing, file
worker and file-engine changes are new. Portable fixture/regression tests pass here; actual WPF,
Windows DPAPI, process ownership and editor behavior require the installer and the session above
on your Windows PC. Installation success alone does not prove all live scenarios.
