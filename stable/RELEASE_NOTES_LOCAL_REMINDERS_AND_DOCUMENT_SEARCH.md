# Cypher 10.9.0 — local reminders and mixed-format document search

This milestone adds two explicit, local workflows to the resident Ctrl+Alt+Space app.

## Use

- `Remind: 2026-09-27 14:30 : Check the project notes` saves a one-time reminder in the PC's local time zone.
- `Remind: list` shows pending reminders. `Remind: cancel ID` removes one pending reminder.
- `Docs: search-all ROOT : project deadline` searches current extractable text in approved TXT, PDF, DOCX, PPTX and XLSX files. `Docs: search ROOT : query` retains its faster plain-text-only behavior.

The reminder store is encrypted for the current Windows user using DPAPI. Cypher must be running to notify at the scheduled time; overdue reminders notify when Cypher next starts. Notification delivery is marked before displaying the tray balloon, so a crash between those two steps could lose that balloon. There is no recurring schedule, background Windows service, cloud sync or voice alert. Reminder contents never go to Hermes, Ollama or a web service.

`search-all` stays inside one named read grant. It scans at most 40 files, 16 MiB of source bytes, 2,000 entries, 100 folders and six levels, with a 45-second scan deadline and separately bounded parser children. It displays at most 20 exact excerpts with file hashes and page, paragraph, slide, sheet or line locations. Unsupported, encrypted or malformed documents are skipped with partial-coverage reporting. There is no saved index, model call, OCR, macro or formula execution, public request or file change. Image-only PDFs still need OCR.

The monochrome command workspace, reviewed Windows actions, bounded public-web routes, local model chat, file operations, and earlier document commands remain available. This does not complete open-ended browser automation, vision input, voice, long-running workflows, external-service integration or a production security audit.

Install with `INSTALL_CYPHER_LOCAL_REMINDERS_AND_DOCUMENT_SEARCH.cmd`. The installer runs preflight tests and retains the rollback host. Previous 10.8.0 package remains intact.
