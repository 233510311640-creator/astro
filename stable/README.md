# Cypher — local Windows assistant

Current bundle: **Core Preview 10.20.3 Chat Shortcut Fix**. Press Ctrl+Alt+Space to speak without opening the chat; hold Ctrl+Win+Alt together to open the chat for typing or review. The tray remains an alternative way to open it.

The END MIC handoff now keeps recognized words even if Windows labels its asynchronous stop event as cancelled. Those words appear as an editable draft in the input box; only **Send** submits them. This fixes the case where Cypher showed WORDS HEARD but then left the input empty. See `RELEASE_NOTES_VOICE_DRAFT_HANDOFF.md`.

While MIC is active, Cypher now shows the microphone signal level and whether speech was heard. It no longer silently discards low-confidence recognized words; uncertain words are placed in the input box with a warning for you to correct before Send. If nothing is recognized, the status distinguishes no microphone signal from speech that Windows could not understand. See `RELEASE_NOTES_VOICE_FEEDBACK_FIX.md`.

Click **MIC** to dictate for up to 20 seconds, then click **END MIC** (or wait) to put the recognized words in the input box. Check or edit the text, then press **Send**. Voice input never submits a request or approves an action by itself. Click **READ ALOUD** to hear the current response; click **STOP AUDIO** to stop. Both use installed local Windows speech components. Stop, Hide, Pause and Exit stop voice activity. There is no wake word, continuous listening, or saved raw audio. Speech accuracy depends on the installed Windows recognizer and microphone. See `RELEASE_NOTES_LOCAL_VOICE.md`.

The left rail now has an **ASK IMAGE** starter for the approved-PNG command.
Use `Files: folders` to find your approved folder name, then replace the example
root, image name and question. The default vision role now uses the installed
Qwen 3.5 9B model. A two-image local sanity check favored it over the previous
Gemma default; this is not a general accuracy guarantee. See
`RELEASE_NOTES_VISION_ACCESS.md`.
The supplied Cypher reference PNG's embedded non-image metadata is now removed
in memory before local inference; the source file stays unchanged.

Use `Vision: describe ROOT "image.png"` or `Vision: ask ROOT "image.png" : QUESTION`
for one PNG in a named approved read folder. Cypher checks the image structure and
the configured installed vision model, then makes one local model call. Its
description may be wrong and is not verified OCR. No attachment, camera, screen
capture, file change, web request or Windows action is enabled by this route.
See `RELEASE_NOTES_APPROVED_PNG_VISION.md`.

Use `Docs: answer-all ROOT : question` to ask one question across current approved
TXT, PDF, DOCX, PPTX and XLSX files. Cypher selects small anonymous excerpts for
one verified local-model call, then shows every cited source file, hash, location
and exact quote. Coverage limits are explicit. There is no saved index or file
change. See `RELEASE_NOTES_CROSS_DOCUMENT_ANSWERS.md`.

Use `Remind: YYYY-MM-DD HH:MM : message` to save a one-time, Windows-user-encrypted
local reminder. `Remind: list` and `Remind: cancel ID` manage pending reminders. The
resident app must be running to deliver a tray notification; overdue reminders
notify when it next starts. Reminder text is not sent to a model or web service.

Use `Docs: search-all ROOT : query` to search extractable text in current approved
TXT, PDF, DOCX, PPTX and XLSX files. It uses strict scan and parser limits, shows
exact located excerpts, and creates no saved index. `Docs: search` remains the
faster plain-text-only option. See `RELEASE_NOTES_LOCAL_REMINDERS_AND_DOCUMENT_SEARCH.md`.

Cypher can now try one explicit public site search with `Web: search URL : QUERY`. It checks
the supplied page for one unambiguous same-host GET search destination and field, sends only
your typed query, then previews exact text from the fetched page. Identical desktop/mobile
search boxes count as one destination. POST, hidden-field, off-site and ambiguous forms fail
closed. The query may reach the site; no browser profile or model is used. Some sites require
JavaScript to display actual matches, which Cypher does not execute.

Cypher can now inspect one public page's eligible HTML forms with `Web: forms URL`. It reports
up to five same-host forms, each with up to eight named non-sensitive fields, the declared method
and destination. It does not display field values or submit anything. This is static HTML
inspection, not a claim that a browser has rendered or enabled the controls.

Cypher can now read one numbered destination from a fresh public-page link map with
`Web: follow URL : NUMBER`. Run `Web: links URL`, then copy the displayed Read command for the
link you want. Cypher fetches the source page again, selects the current numbered same-host link,
and returns exact excerpts from that destination. No browser profile, cookies, login, scripts,
forms, download, local model, file or Windows action is connected. A changed page can change the
numbering; Cypher reports when a selected number is no longer present.

Cypher can now map visible navigation choices from one explicit page with `Web: links URL`.
The isolated, model-free reader returns at most six eligible same-site HTTPS links and does not open
them. Each result includes a separate exact browser command; submitting it uses the existing
executable-bound and destination-bound one-time approval. Hidden, form, script, fragment,
credential-like, signed, off-site and common download targets are excluded.

Cypher can now answer a focused question about one explicit public HTTPS page with
`Web: ask URL : QUESTION`. The same isolated public-page reader supplies only bounded passages to
at most one verified installed local-model call. Every displayed finding must select valid
reader-assigned passage IDs and is shown with exact supporting source text. The route cannot access
a browser profile, cookies, login state, scripts, files, or Windows actions, and page text remains
untrusted data.

Cypher can now preview one explicit public HTTPS page with `Web: read URL` or `Web: preview URL`.
The isolated reader applies public-address, DNS, robots, redirect, content-type, response-size, and
time limits, then displays at most four exact bounded excerpts. It has no access to a browser
profile, cookies, saved passwords, login state, scripts, local files, Windows actions, or a model.
Page text is always treated as untrusted data and cannot authorize an action.

Cypher now accepts bounded natural browser searches such as `Search the web for local AI assistants
in Brave` or `Open Chrome then search chess openings`. The exact query, fixed DuckDuckGo destination,
and browser executable appear in the one-time approval before anything is sent. Domain-like values
such as `chess.com` continue to open directly instead of becoming searches. Cypher still does not
read results, click pages, use browser profiles, or claim that a page loaded.

Cypher can now open a public HTTPS destination in Brave, Microsoft Edge, Google Chrome, or Mozilla
Firefox without manually adding that browser first. It discovers only fixed standard installation
locations, then binds the exact executable and destination into the existing one-time approval.
Other applications still require explicit registration. This is safe destination delivery, not
autonomous page reading or website interaction.

Open Cypher's monochrome signal workspace from its tray icon: a high-contrast,
opaque black command center with off-white typography, technical framing, real system rails and
semantic color reserved for state, approval, success and failure. The scalable line icons and
verified original machine-intelligence hero image from 9.7.1 remain. The design is original to
Cypher and does not copy the reference artwork or its text.

Bounded Office Documents adds explicit DOCX, PPTX, and XLSX support to document ask, answer,
summarize, and comparison. Office bytes go to a separate integrity-pinned, path-free parser with
strict ZIP/XML resource limits. Word paragraphs, PowerPoint slides, and Excel sheet rows receive
exact evidence locations. Macros and formulas never execute.

The HTTPS Open route fixes the screenshot failure where `open brave then search chess.com` fell
through to general chat. The exact natural form now routes locally before the model, normalizes one
domain to HTTPS, resolves a registered application or a supported auto-discovered browser, and shows
the executable plus exact destination in a 60-second one-time approval. It sends one argument and
does not inspect page data.

The retained PDF Documents milestone extends explicit ask, answer, summarize and two-to-four-source comparison to local
PDF files up to 8 MiB / 100 pages. PDF bytes go to a separate pinned parser child with no path,
question, model or action context. Exact evidence gains page references. The 1 MiB text-document,
plain-text search and fixed 4,096-byte model-evidence limits remain.

**Install:** keep the current release for rollback, extract the whole ZIP into a new folder, then run
**INSTALL_CYPHER_VOICE_DRAFT_HANDOFF.cmd** normally. Confirm **CORE PREVIEW 10.13.2 / MONOCHROME SIGNAL**.

Start with:

```text
Web: links https://example.org/
Web: follow https://example.org/ : 1
Web: forms https://example.org/
Web: search https://docs.python.org/3/ : asyncio
```

Or use documents:

```text
Docs: ask work "proposal.docx" : What delivery date is promised?
```

See **[Bounded Site Search setup](BOUNDED_SITE_SEARCH_SETUP.md)** for commands and limits. Existing
HTTPS-open/PDF/file/search/read acceptance results remain valid; do not repeat them.

[Site search release](RELEASE_NOTES_BOUNDED_SITE_SEARCH.md) · [Site search validation](VALIDATION_BOUNDED_SITE_SEARCH.md) · [Site search security](SECURITY_BOUNDED_SITE_SEARCH.md) ·
[Form inspection release](RELEASE_NOTES_BOUNDED_FORM_INSPECTION.md) · [Form inspection validation](VALIDATION_BOUNDED_FORM_INSPECTION.md) · [Form inspection security](SECURITY_BOUNDED_FORM_INSPECTION.md) ·
[Navigation release](RELEASE_NOTES_BOUNDED_WEB_NAVIGATION.md) · [Navigation validation](VALIDATION_BOUNDED_WEB_NAVIGATION.md) ·
[Navigation security](SECURITY_BOUNDED_WEB_NAVIGATION.md) · [Web-answer release](RELEASE_NOTES_GROUNDED_WEB_ANSWERS.md) · [Web-answer validation](VALIDATION_GROUNDED_WEB_ANSWERS.md) ·
[Web-answer security](SECURITY_GROUNDED_WEB_ANSWERS.md) · [Page-read release](RELEASE_NOTES_ISOLATED_PAGE_READ.md) · [Page-read validation](VALIDATION_ISOLATED_PAGE_READ.md) ·
[Page-read security](SECURITY_ISOLATED_PAGE_READ.md) · [Office release](RELEASE_NOTES_OFFICE_DOCUMENTS.md) · [Office validation](VALIDATION_OFFICE_DOCUMENTS.md) ·
[Office security](SECURITY_OFFICE_DOCUMENTS.md) · [HTTPS Open release](RELEASE_NOTES_REGISTERED_HTTPS_OPEN.md) · [HTTPS Open validation](VALIDATION_REGISTERED_HTTPS_OPEN.md) ·
[HTTPS Open security](SECURITY_REGISTERED_HTTPS_OPEN.md) · [PDF Documents release](RELEASE_NOTES_PDF_DOCUMENTS.md) · [PDF validation](VALIDATION_PDF_DOCUMENTS.md) ·
[PDF security](SECURITY_PDF_DOCUMENTS.md) · [Workspace release](RELEASE_NOTES_DOCUMENT_WORKSPACE.md) ·
[Document feature notes](RELEASE_NOTES_DOCUMENT_ANSWERS.md) · [Document validation](VALIDATION_DOCUMENT_ANSWERS.md) ·
[Document boundary](SECURITY_DOCUMENT_ANSWERS.md) · [Roadmap](docs/CYPHER_NEXT_MILESTONES.md).

Files: commands and Runtime: diagnostics remain available. Existing file-change approvals and undo
are retained. Explicit Docs routes support UTF-8 text up to 1 MiB and PDF/DOCX/PPTX/XLSX files up
to their documented limits. Legacy/macro-enabled Office documents and OCR remain unavailable.
Search is a bounded plain-text live scan, not an index,
and makes no model call. No public request, model download, retry, file
modification or history addition is introduced. Grounding checks reduce unsupported prose but do
not prove entailment; the exact cited evidence remains authoritative.

Older component guides below are reference material, not additional upgrade prerequisites.

## What v0.8 Alpha 1 adds

- replaceable fast/deep/vision model roles with bounded sequential hand-offs;
- human-managed per-folder capability scopes;
- bounded real-folder text reads;
- approval-gated create, replace, copy, move, rename, directory creation and quarantine;
- encrypted action and undo payloads using Windows current-user DPAPI;
- up to 50 actions in one verified batch with collision checks and rollback;
- restart reconciliation that fails closed when safe recovery cannot be proved; and
- metadata-only operation status and audit evidence.

Alpha 1.3 has passed 173 source/regression tests. It is not the verified Windows baseline until the
target-PC installation, DPAPI, Hermes registration, action, restart and undo acceptance tests pass.

## What the v0.7 Core Preview adds

- a compiled Windows resident executable built locally with the .NET Framework included in Windows 11;
- deterministic, model-free read-only Windows observation for registered applications and titled top-level windows;
- deterministic registered-app launch and exact visible-window focus after a fresh native one-time approval;
- one validated public HTTPS destination sent to one exact registered app after a fresh native one-time approval;
- bounded enumeration of actionable controls in one visible human-registered application window;
- exact packaged-app matching through a human-registered Windows `AppUserModelID`;
- one no-ID `Open <registered app> and write: <text>` workflow behind one approval;
- native one-time approval for exactly one UI Automation Invoke, Toggle, Select, Expand, Collapse, or separately enabled Set Text action;
- bounded 500-character in-memory text delivery without reading the control's existing Value/Document text;
- target-bound SHA-256/metadata fingerprints, expiry, replay rejection, target revalidation, and local postcondition evidence for Windows actions;
- Hermes Runs API + SSE streaming instead of the blocking `/v1/responses` path;
- verified run cancellation from a **Stop** button;
- native **Approve once** and **Deny** controls for Hermes approval requests;
- visible task lifecycle and observed evidence status;
- an immediate memory-only activity view showing the request, selected model, phase, elapsed time, and streaming transition;
- metadata-only task checkpoints and authoritative Hermes status reconciliation after a Cypher restart or lost stream;
- content-free terminal-failure receipts containing only a run ID, model profile, failure stage,
  timestamp and aggregate tool-event counts;
- a visible recovery state that refuses to guess success, silently repeat work, or approve an action without its review details;
- deterministic local Auto/Fast/Deep/Vision model routing based on the target-PC benchmark;
- memory-only bounded recent context; and
- transactional installation beside v0.6.3 with cooperative rollback.

The checkpoint contains a run identifier, model profile, lifecycle phase, timestamps, and aggregate tool-event counts only. It never stores prompts, answers, filenames, tool arguments, approval content, or conversation history. The preview does not enable new Hermes tools, broaden MCP roots, change model files, enable microphone access, request administrator rights, or log prompts/responses. The final v0.7 WinUI 3 shell, richer sessions, and resource modes remain in development.

## What v0.6 adds

After one visible installation, normal conversations no longer require opening PowerShell or the Hermes TUI. The resident host:

- starts at Windows sign-in as the current standard user;
- keeps Hermes' supported gateway running without a visible terminal;
- appears in the Windows notification area;
- opens with `Ctrl+Alt+Space` or a tray-icon double-click;
- sends commands to Hermes through an authenticated, loopback-only API;
- preserves conversation context through a named local Hermes conversation; and
- shows the final response in a small Windows window.

v0.6.3 replaces the temporary grey prompt and response dialogs with one borderless WPF interface. Prompts, thinking state, formatted responses, copy, and new-conversation controls now remain in the same native window. It does not use WebView, a browser, or a remote UI.

This milestone deliberately does **not** listen to the microphone. Push-to-talk and an optional local wake word come after the resident text path is stable. It also does not add any new computer authority: all unrestricted Hermes built-ins stay disabled and the existing MCP broker remains the tool boundary.

## What v0.5 already provides

v0.5 adds a persistent **dry-run graphic-file organizer**. Hermes may draft a move plan only after a person separately approves both:

- a metadata-only source inventory root; and
- a planning-only destination root.

The plan can include extension-classified graphic candidates, proposed destination paths, short reasons, source metadata snapshots, an expiry, and a SHA-256 fingerprint. It cannot execute. There is deliberately no real-folder apply, move, copy, rename, delete, directory-creation, shell, or arbitrary-file tool in v0.5.

Human review records acceptance of the dry run only. It grants no file permission and does not create the proposed folders.

## Current architecture

- Hermes Agent provides orchestration and tool calling.
- `local-assistant-brain-64k:latest` runs locally through Ollama with a 65,536-token context.
- All unrestricted Hermes built-in tools remain disabled.
- One custom MCP broker exposes exactly twenty-eight narrow tools in the current v0.8 candidate.
- Eight tools retain the v0.3.3 sandbox proposal, approval, execution, and undo workflow.
- Four v0.4 tools provide metadata-only inventory for explicitly allowlisted real folders.
- Four v0.5 tools provide status, proposal, retrieval, and validation for dry-run organization plans.
- Six v0.8 tools expose permission metadata, bounded text read, proposal/retrieval,
  apply-after-external-approval and metadata-only operation status. Permission changes, approval and
  undo remain human-side only.
- Six v0.8.1 Windows-operator tools expose bounded status, app/window observation, exact registered-app
  launch and exact visible-window focus; the compiled resident host handles observation, launch/focus,
  exact packaged-app identity and single-control UI Automation deterministically for reliability.
- Preview 9.2.7 research is a separate native input route and standard-library Python worker, not a new Hermes/MCP tool. The fixed Wikipedia/OpenAlex lookups, exact-503 Crossref fallback, local abstract ranking, and direct-evidence guard never grant broker or Windows authority. The worker job blocks desktop/clipboard interaction but is not yet an AppContainer filesystem/network sandbox.

## Safety and privacy boundary

No real source or destination folder is enabled during setup. Human-side PowerShell commands manage those permissions; Hermes cannot call those commands.

Inventory and organization planning never open real-folder file contents. Graphic classification is based only on file extensions. Plans preserve exact filenames, refuse overwrite, reject traversal, links/reparse points, deceptive formatting characters, unsafe Windows names, duplicate sources or destinations, changed source metadata, and newly appeared destination conflicts. A plan is limited to 50 items and 60 minutes, with proposal and storage caps.

Inventory audit events exclude scanned filenames and contents. The local organization plan database necessarily stores the filenames, proposed paths, reasons, metadata snapshots, roots, and fingerprints needed for human review. See [`SECURITY_BROKER_V0.5.md`](SECURITY_BROKER_V0.5.md) for exact limitations.

## Existing sandbox actions

Inside `Desktop\Hermes Sandbox`, Hermes can list and read small approved text files and propose creating/replacing text, creating a directory, or moving one item. Those sandbox proposals make no change until an exact external approval, and protected undo remains human-side. This is separate from real-folder organization, which stays non-executable in v0.5.

## Still unavailable

No raw shell, arbitrary code, unrestricted file access, interactive browser automation, unrestricted computer control,
credentials, messaging, administrator access, wake-word listening, permanent delete, or unattended
autonomous task execution is exposed. The v0.8 candidate adds only approval-gated mutation inside
separately registered roots. Core Preview 9.2.7 retains an exact registered-app launch,
exact listed-window focus, one approved UI Automation Invoke/Toggle/Select/Expand/Collapse action,
the no-ID registered-app write workflow, and explicit ordered workflows using the five supported
app actions. A registered app may separately receive bounded Set Text authority;
this is not raw typing and cannot read the existing field. Cypher cannot send raw mouse/keyboard
events, use the clipboard, consume coordinates, inspect password values, capture the screen, run
commands, execute arbitrary control chains, or create lasting approval. The resident host itself runs in the
background, but it acts only when the user activates it.

The long-term architecture and staged roadmap are documented in [`docs/ASSISTANT_FOUNDATION_SPEC.md`](docs/ASSISTANT_FOUNDATION_SPEC.md).

Supplementary C# validation: workflow cases 100–147 passed under Linux Mono. The old single-wait
method fails deterministic early-wake case 140; the corrected method passes. This does not replace
the native WPF/Windows installer gate. See `RELEASE_NOTES_OBSERVATION_DEADLINE_FIX.md`.
