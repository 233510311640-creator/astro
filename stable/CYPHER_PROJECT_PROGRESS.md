# Current bundle: 10.13.2 Voice Draft Handoff Fix

27 September 2026. The user reported WORDS HEARD while recording, followed by
an empty input box after END MIC. Resident metadata logs showed each such
completion recorded as cancelled. The host had been treating the Windows
recognizer's Cancelled completion flag as equivalent to the user's Stop action
and discarding its already captured words. This update separates the two:
END MIC retains the draft unless there is an error, while explicit Stop still
discards it. A native self-test covers engine-cancelled completion and actual
insertion into a bounded WPF input box. No transcript is logged or auto-sent.

Validation: 594 Python tests (593 pass, one existing skip), the native host
including its draft-handoff self-test, owned-worker checks and Hermes preflight
passed before installation. The resident heartbeat reports READY on 10.13.2
and an offscreen 1120 × 720 render fits the controls. The screenshots supplied
for this report predate the 10.13.2 restart; no live MIC attempt on the new
version has yet been recorded.

## Previous bundle: 10.13.1 Voice Feedback Fix

27 September 2026. User testing found NO SPEECH although the Windows microphone
worked elsewhere. The prior app filtered all recognized results below 0.45
confidence and showed no microphone level or rejection signal. This update
keeps low-confidence words as an explicitly uncertain draft, adds a live input
level and speech-detected status, distinguishes missing input from unrecognized
speech, adds a five-second completion fallback, and records metadata-only voice
outcomes for diagnosis. Send and existing approvals remain mandatory.

Validation: 594 Python tests (593 pass, one existing skip), compiled WPF host,
owned-worker checks and authenticated Hermes preflight passed before the
transactional upgrade. The installed heartbeat reports READY on 10.13.1, and
an offscreen 1120 × 720 render shows the expected controls. A matching en-US
synthetic-voice test demonstrated that Windows can recognize a phrase, but no
post-fix live microphone phrase has been verified yet.

## Previous bundle: 10.13.0 Local Voice

27 September 2026. The Ctrl+Alt+Space workspace now has an explicit MIC control
for up to 20 seconds of local Windows speech recognition. Its transcript is
placed in the input box for review; only Send submits it. READ ALOUD speaks a
bounded part of the current response through an installed local Windows voice.
Stop, Hide, Pause and Exit stop voice activity. No wake word, continuous capture
or saved raw audio. See `RELEASE_NOTES_LOCAL_VOICE.md` and validation notes.

Validation: 594 Python tests passed except one existing platform skip; compiled
WPF host and owned-worker self-tests passed before installation. The installed
recognizer accepted the default microphone (`en-US`) and a 1120 × 720 workspace
render showed both controls. The resident heartbeat reports READY on 10.13.0.
No spoken phrase was available to measure transcription accuracy.

## Previous bundle: 10.12.0 Vision Access and Model Tuning

27 September 2026. The Ctrl+Alt+Space left rail now exposes an ASK IMAGE starter
that fills an explicit approved-PNG question without sending it. Session details
explain how to find the approved folder name with `Files: folders`; the stale
"image input not connected" line is gone. The default vision role changes from
Gemma 4 E4B to the already installed Qwen 3.5 9B after Qwen correctly named a
synthetic red image and identified the subject and layout of the supplied Cypher
reference artwork in two local checks. Gemma missed the solid color and central
subject in those checks. Neither small check proves general accuracy.

Validation: 593 tests (592 pass, one existing skip), native and four owned-worker
self-tests, authenticated Hermes preflight, transactional installation, READY
heartbeat, Qwen vision sanity checks, and the supplied PNG's metadata-removal
path passed. The installed worker matches its release pin. See
`VALIDATION_VISION_ACCESS.md`.

## Previous bundle: 10.11.0 Approved PNG Vision

27 September 2026. Explicit `Vision: describe ROOT "image.png"` and
`Vision: ask ROOT "image.png" : QUESTION` read one PNG from a named approved
folder through the isolated document worker and send it to the configured,
installed local vision model. PNG size, dimensions and structure are bounded;
the answer is labeled unverified interpretation. No screenshot, attachment,
camera, public web access, Windows action, file change or chat-history addition.

Validation: 592 tests (591 pass, one existing skip), native compilation and
self-test, all four owned-worker self-tests, Hermes capability preflight,
transactional installation and a READY heartbeat passed. The installed document
worker matches the release integrity pin. No live user-image inference ran.

## Previous bundle: 10.10.0 Grounded Cross-Document Answers

26 September 2026. `Docs: answer-all ROOT : question` scans one named approved
folder with the bounded mixed-format document reader introduced in 10.9.0. It
selects a small question-relevant set from at most four files, sends no file
paths and at most 4,096 text bytes to one verified installed local model, and
shows a short checked answer with exact cited file paths, hashes, locations and
quotes. Missing or unsupported evidence is withheld. It creates no saved index
or file change and does not add the result to chat history.

Validation: 587 Python tests (586 pass, one existing platform skip), direct
document-worker self-test, native compilation, WPF host self-test, all four
owned-worker self-tests, authenticated Hermes capability preflight, transactional
installation and a READY heartbeat for `0.7.0-core-preview10.10.0` passed.

## Previous bundle: 10.9.0 Local Reminders and Mixed-Format Document Search

26 September 2026. The resident app now accepts explicit one-time local reminders,
stores them under the current Windows user's DPAPI protection, and shows tray
notifications while running or after the next start if a reminder became overdue.
Pending reminders can be listed or cancelled. No reminder content goes to Hermes,
Ollama, or a web service.

`Docs: search-all ROOT : query` expands bounded folder content search to extractable
PDF, DOCX, PPTX and XLSX text alongside plain text, using existing named folder
grants and pinned parser children. It creates no saved index and makes no model call.

Validation: 582 Python tests (581 pass, one existing platform skip), native
compilation, and the compiled host self-test including WPF layout and reminder
round-trips passed. The installer's preflight stopped before installation because
the current tool sandbox could not read the installed Ollama executable; an
escalated retry was rejected by the app's approval reviewer due to its usage
limit. The installed 10.8.0 resident app remains unchanged. Native owned-worker
self-tests and a live 10.9.0 heartbeat remain unverified in this environment.

## Previous bundle: 10.8.0 Bounded Public Site Search

26 September 2026. `Web: search PUBLIC-HTTPS-URL : QUERY` accepts one explicitly
typed bounded query, checks an isolated public page for one unique same-site GET
search action and field, then previews exact text from the fetched page. Identical
search boxes are deduplicated. POST, hidden-field, off-site and ambiguous forms
reject before a query request; robots and redirect boundaries remain in force.

Validation: 580 tests (579 pass, one existing skip), native compilation and self-test,
owned-worker checks, WPF layout, transactional install and READY heartbeat. A live
installed-worker check on Python documentation completed with two pages and four exact
excerpts. JavaScript-generated matches are not rendered.

## Previous bundle: 10.7.0 Bounded Public Form Inspection

26 September 2026. `Web: forms PUBLIC-HTTPS-URL` reports bounded static HTML form
metadata from one isolated public page: same-host action, declared method and named
non-sensitive field types. It excludes values, hidden/password/file controls and any
filling or submission. The desktop rail includes an Inspect Forms starter.

Validation: 575 tests (574 pass, one existing skip), native compilation, compiled
self-test, owned-worker checks, WPF render, transactional install and READY heartbeat.
A live Wikipedia Main Page inspection read one page and returned two form structures.

## Previous bundle: 10.6.0 Bounded Public Link Follow

26 September 2026. `Web: follow PUBLIC-HTTPS-URL : NUMBER` rebuilds the current visible same-host
link map and reads only the selected destination through the isolated, model-free reader. The
map now prints a Read command next to each link; the desktop rail has a Follow Link starter.
The second page is checked under the source host restriction, including redirects. Up to four
exact destination excerpts are displayed. No browser state, form, script, local model, file or
Windows action is available. A changed or missing number is reported without another page read.

Validation: 571 tests (570 pass, one existing skip), native compilation, compiled self-test,
owned-worker checks, workspace render, transactional install and READY heartbeat. The installed
research worker matches the release hash. One live Wikipedia follow completed with two pages
read and four exact excerpts.

## Previous bundle: 10.5.0 Bounded Public Page Navigation

25 September 2026. `Web: links PUBLIC-HTTPS-URL` and `Web: map PUBLIC-HTTPS-URL` now read exactly
one explicit public page through the isolated model-free reader and return at most six visible,
deduplicated, eligible same-site HTTPS navigation links. Off-site and hidden links, forms, fragments, scripts,
credential-like or signed URLs, local/private targets and common download-file targets are excluded.

The map never opens a link. Every displayed result includes a separate exact browser command which
uses the existing fixed-path/registered browser checks and destination-bound one-time approval.
The route has no browser profile, cookie, login state, script engine, form submission, click,
download, model call, file access, Windows action, shell, retry or durable history.

See RELEASE_NOTES_BOUNDED_WEB_NAVIGATION.md, SECURITY_BOUNDED_WEB_NAVIGATION.md and
VALIDATION_BOUNDED_WEB_NAVIGATION.md.

The full suite runs 566 tests: 565 pass and one existing platform skip. Native compilation,
compiled self-test, owned research/file/runtime/document worker tests, WPF workspace rendering and
transactional installation pass. The resident host reports READY on
`0.7.0-core-preview10.5.0`; the installed research worker matches the release hash. A live
Wikipedia link map completed with six same-host results and opened no destination.

## Previous bundle: 10.4.0 Grounded Public Page Answers

25 September 2026. `Web: ask PUBLIC-HTTPS-URL : QUESTION` now reads exactly one explicit public
page through the isolated reader, ranks bounded passages against the question, and gives only those
passages to at most one verified installed local-model call. Each displayed finding must select
valid reader-assigned passage IDs, pass the existing claim-scope checks, and show exact supporting
page text. The page remains untrusted and cannot approve or start an action.

The route has no browser profile, cookies, login state, scripts, file tools, Windows actions, shell,
provider discovery, fallback, or automatic retry. The question and model call stay local; only the
explicit page request leaves the PC. See RELEASE_NOTES_GROUNDED_WEB_ANSWERS.md,
SECURITY_GROUNDED_WEB_ANSWERS.md and VALIDATION_GROUNDED_WEB_ANSWERS.md.

All 562 automated tests pass with one existing platform skip. Native compilation, compiled
self-test, owned-worker isolation fixtures, and transactional installation pass. The live host
reports READY on `0.7.0-core-preview10.4.0`; installed research, file, and document worker hashes
match the release. A real example.org page question completed with one checked finding and exact
supporting text.

## Previous bundle: 10.3.0 Isolated Public Page Read

21 September 2026. `Web: read PUBLIC-HTTPS-URL` and `Web: preview PUBLIC-HTTPS-URL` now read
exactly one explicit public page through the isolated research worker without discovery or a model
call. Cypher applies the existing public-IP, DNS, robots, redirect, content-type, byte, and time
limits and returns at most four exact excerpts. The route has no browser profile, cookies, login,
scripts, file tools, Windows actions, or shell access. Page content is untrusted and cannot approve
or start an action.

All 559 automated checks pass with one existing platform skip. Native compilation, compiled
self-test, owned-worker isolation fixtures, and transactional installation pass. The live host
reports READY on `0.7.0-core-preview10.3.0`; its installed research, file, and document worker
hashes match the release. See RELEASE_NOTES_ISOLATED_PAGE_READ.md,
SECURITY_ISOLATED_PAGE_READ.md and VALIDATION_ISOLATED_PAGE_READ.md.

## Previous bundle: 10.2.0 Bounded Office Documents

20 September 2026. Explicit Docs ask, answer, summarize and comparison now accept bounded DOCX,
PPTX and XLSX files. A separately pinned standard-library parser receives only verified bytes and
returns bounded paragraph, slide or sheet/row text. It has no path, grant, question, model, network
or action engine. Archive/XML limits reject traversal, duplicate names, encryption, extreme
expansion, DTD/entities, malformed relationships, macro formats and format/extension mismatches.
Macros and formulas never execute.

The focused document suite has 52 passing tests and the combined document/native-host gate has 108.
The complete suite runs 555 tests: 554 pass and one existing direct-run Windows platform check skips.
Native build, compiled self-test, offline fixtures, WPF render and transactional installation pass.
The live host reports READY on `0.7.0-core-preview10.2.0`; installed document, PDF, Office and file
worker hashes exactly match this package. See
RELEASE_NOTES_OFFICE_DOCUMENTS.md, SECURITY_OFFICE_DOCUMENTS.md and VALIDATION_OFFICE_DOCUMENTS.md.

## Previous bundle: 10.1.1 Registered HTTPS Open

19 September 2026. 10.1.1 fixes the routing gap shown by `open brave then search chess.com`.
The phrase now stays out of general chat and becomes one deterministic native proposal for an exact
human-registered app and one validated public HTTPS destination. The app record, executable metadata
and SHA-256, normalized destination length/SHA-256, selection policy and expiry are fingerprinted.
Only the native approval can execute it. Non-HTTPS, local, IP-literal, credentialed, multi-destination
or unregistered targets fail closed. Cypher verifies local delivery to the registered app/process but
does not claim that a page loaded because it never reads the address bar or page.

The focused Windows-host suite has 56 passing tests. The complete suite runs 550 tests: 549 pass and
one existing direct-run Windows platform check skips. Native build, compiled self-test, offline
fixtures, WPF render and transactional installation pass. The live host reports READY on
`0.7.0-core-preview10.1.1`, and its installed document, PDF-parser and file-worker hashes match this
package. See RELEASE_NOTES_REGISTERED_HTTPS_OPEN.md, SECURITY_REGISTERED_HTTPS_OPEN.md and
VALIDATION_REGISTERED_HTTPS_OPEN.md.

## Previous bundle: 10.1.0 Bounded PDF Documents

19 September 2026. 10.1.0 extends explicit Docs ask, answer, summarize and comparison to PDFs up to
8 MiB / 100 pages. A separate integrity-pinned parser child receives bytes but no file path, grant
store, question, model endpoint or action engine. Evidence retains the fixed 4,096-byte model limit
and gains exact PDF page/line references. Encrypted, malformed and over-limit PDFs reject before
model access; image-only PDFs have no OCR. Text-only folder search remains unchanged.

All 47 focused document/PDF tests and 69 combined document/reader tests pass. Native compilation,
the executable self-test, owned parser-child fixture and WPF render pass. The complete regression
suite runs 549 tests: 548 pass and one existing direct-run Windows platform check is skipped; the
required Windows-native gates pass separately. Transactional installation passes. The live host is
READY on `0.7.0-core-preview10.1.0`, and its installed document, PDF-parser and file-worker hashes
match this package. The complete 10.0.0 package remains the immediate rollback release. See
RELEASE_NOTES_PDF_DOCUMENTS.md, SECURITY_PDF_DOCUMENTS.md and VALIDATION_PDF_DOCUMENTS.md.

## Previous bundle: 10.0.0 Bounded Document Workspace

18 September 2026. 10.0.0 adds model-free bounded content search inside one explicitly granted
folder, raises explicit Docs routes to 1 MiB UTF-8 text files, and expands grounded comparison to
two, three or four named files. Search creates no index or model request. Generated routes keep the
same fixed 4,096-byte evidence ceiling, and comparison requires exact cited evidence from every
supplied source.

The native system rail adds **03 DOC SEARCH** and retains dedicated answer and compare prompt
starters. The complete suite runs 541 tests: 540 pass and one existing Windows-only check is skipped.
All 40 focused document tests pass. Native build, render and transactional installation pass; the
live 10.0.0 heartbeat is READY and its worker hashes match the package. See RELEASE_NOTES_DOCUMENT_WORKSPACE.md,
SECURITY_DOCUMENT_WORKSPACE.md and VALIDATION_DOCUMENT_WORKSPACE.md.

## Previous bundle: 9.9.0 Grounded Two-Document Compare

18 September 2026. 9.9.0 adds an explicit `Docs: compare` route for exactly two named granted UTF-8
text files. Source A and Source B receive independent bounded evidence sets and source-scoped IDs.
One installed local-model generation may draft at most four short sentences, but a non-empty result
must select and reference passages from both sources. Cypher displays every exact supporting quote,
source label, line number, snapshot time, byte count and digest below the generated comparison.

The route rechecks both grants immediately before model input and before display. It rejects
duplicate command references, one-sided/forged/unused IDs, unsupported numbers, unrelated wording,
URLs, control text, remote aliases and malformed output without retry. Empty or insufficient
evidence yields a partial result rather than an invented difference. These checks do not prove
entailment; exact cited evidence remains authoritative.

The native system rail adds **04 DOC COMPARE** and renumbers New Chat/Copy without changing their
behavior. The focused document suite has 33 passing tests; the full suite runs 534 tests, with 533
passing and one existing Windows-only skip. Native compilation, self-test, WPF render and the
transactional installer pass. The live host reports READY on 9.9.0 and its installed isolated-worker
hashes match the package. See RELEASE_NOTES_GROUNDED_COMPARE.md,
SECURITY_GROUNDED_COMPARE.md and VALIDATION_GROUNDED_COMPARE.md.

## Previous bundle: 9.8.0 Grounded Document Answers

18 September 2026. 9.8.0 adds an explicit `Docs: answer` route for one granted UTF-8 text file.
One installed local-model generation may return at most four short answer sentences, each citing
one or two selected passage IDs. Cypher validates the strict response, checks IDs, exact numbers,
format and conservative wording overlap, then displays the model draft beside the exact supporting
passages and source lines. These controls reduce unsupported output; they do not prove entailment.

The native system rail now includes **03 DOC ANSWER**, an input-only shortcut. Existing extractive
`Docs: ask` and `Docs: summarize` behavior remains. The document worker still has no file-action or
public-research engine, and this milestone adds no broader folder permission, network provider,
retry, model substitution, durable memory or action authority. The full automated suite ran 528
tests: 527 passed and one existing Windows-only test was skipped. See
RELEASE_NOTES_GROUNDED_DOCUMENTS.md, SECURITY_GROUNDED_DOCUMENTS.md and
VALIDATION_GROUNDED_DOCUMENTS.md.

The 9.7.1 Monochrome Signal workspace, scalable title-bar controls and SHA-256-pinned original
artwork remain the Ctrl+Alt+Space visual foundation. Keep the complete 9.7.1 package as reinstall
rollback.

## Previous bundle: 9.7.1 Monochrome Signal

17 September 2026. The user selected a monochrome editorial/cyber-industrial reference for the
Ctrl+Alt+Space experience. 9.7.1 translated its high-contrast mood into a Cypher-owned native WPF
workspace with opaque black surfaces, off-white type, technical hairlines, a subtle signal grid,
asymmetric mode/system rails, scalable line icons and original generated signal artwork. It kept
the complete command, evidence, approval, Stop, recovery and keyboard surfaces.

## Previous bundle: 9.6.0 Document Answers

15 September 2026. The user confirmed 9.5.1 search and complete 101-byte text reading of
Documents/meeting-notes.txt; its displayed digest matches the bundled synthetic note. The Windows
read correction is accepted for that scenario. No repeat search/read or modification check is needed.

9.6.0 adds explicit local-document ask/summarize commands returning exact source passages selected
by one installed local-model call, with checked IDs/line references and disclosed excerpt coverage.
The independent worker, native route, offline installer fixture and portable tests are implemented.
Remaining gate: one live Docs question on the existing synthetic note. No claim of native 9.6.0
execution or improved model performance is made before that result.

## Historical records

# Current correction: 9.5.1

15 September 2026. The user's screenshot shows 9.5.0 failed test_file_tasks.py at the text-read
metadata comparison, before any resident-host change. This patch separates path/handle snapshot
comparisons and retains identity, size, grant, bounded-read and Stop checks. 23 browser tests pass;
full portable suite: 501 discovered, 500 passed, one Windows-only compiler skip. Live Windows
installation remains pending. No claim that the failed 9.5.0 was installed or accepted.

# Current bundle: 9.5.0 File Explorer

11 September 2026. User reported completion of 9.4.0; no benchmark values were attached, so
runtime performance is unmeasured in this record. 9.5.0 adds granted-folder filename search,
nested listing and bounded text reads with zero model calls. Prior apply/undo/permission engines,
research and runtime remain unchanged. Remaining live gate: find/read a known synthetic note.
See FILE_EXPLORER_SETUP.md and VALIDATION_FILE_EXPLORER.md. No repeated file-change test.

## Historical progress record

# Cypher Project Progress

**Status date:** 10 September 2026  
**Current milestone:** v0.9.4.0 Runtime Readiness. Native local status and one-generation measurement, cloud/local-weight checks, cancellation and clearer file receipts are implemented. See VALIDATION_RUNTIME_READINESS.md. Native runtime measurement remains pending.  
**Accepted live file baseline:** 9.3.0 installed, folder grant succeeded, four organization actions verified, undo/reverse changes verified, later Stop before approval cancelled with no action. No claim of a new in-flight Stop or editor regression run is made.  
**Platform:** Windows 11 Pro, standard-user execution  
**Core principle:** Local-first intelligence with capability-based permissions and human approval for consequential actions.

## 1. Project goal

Cypher is being developed as a private, always-available Windows assistant that can understand requests, choose the appropriate local model, use narrowly defined tools, perform supervised work, verify results, and recover safely. It is not designed as an unrestricted “do anything” process. The model proposes; deterministic policy and approved capabilities decide what may happen.

The project remains local by default and does not require paid inference APIs.

## 2. Target system prepared

- Windows 11 Pro x64
- AMD Ryzen 5 9600X
- 32 GB RAM
- AMD Radeon RX 9060 XT with 16 GB VRAM
- BitLocker enabled
- Hardware virtualization enabled
- Ollama restricted to the local loopback interface

## 3. Local intelligence foundation

We installed and verified Ollama as the local model runtime and connected it to Hermes for orchestration. Local requests remain on the PC unless a future, separately reviewed online capability is deliberately enabled.

The target-PC model evaluation established three roles:

| Role | Model | Purpose |
| --- | --- | --- |
| Fast/reflex | `qwen3.5:9b-q4_K_M` | Everyday conversation, routine planning and ordinary tasks |
| Deep reasoning | `gpt-oss:20b` | Difficult analysis, debugging and multi-constraint planning |
| Vision/fallback | `gemma4:e4b` | Future image understanding and compact fallback work |

All three passed the initial instruction-following and safety scenarios. Cypher normally uses one model at a time to avoid exhausting 16 GB of VRAM. Complex future workflows will use parallel tools and sequential specialist models rather than keeping every model loaded simultaneously.

## 4. Hermes and local security audit

We audited the Hermes/Ollama environment without reading conversations, credentials, browser data or personal files. The audit confirmed:

- Hermes and Ollama were installed and reachable locally;
- the Ollama API listened on loopback rather than the LAN;
- available and active model inventory could be checked safely;
- Cypher could use an authenticated local Hermes gateway;
- configuration and content remained outside the read-only audit.

Hermes was then updated through a cautious backup-and-reinstall process while preserving the previous installation for recovery.

## 5. Capability broker milestones

### v0.2 — Read-only sandbox

The first custom broker exposed only three narrow tools inside `Desktop\Hermes Sandbox`:

- show the sandbox boundary;
- list one approved directory;
- read one small UTF-8 text file.

It rejected path traversal, absolute paths, drive paths, symlink escapes, protected files, binary files and oversized files.

### v0.3.3 — Approved and reversible sandbox actions

The broker grew to eight sandbox tools. Cypher could propose:

- creating a small text file;
- replacing a small text file;
- creating a directory;
- moving or renaming one sandbox item without overwrite.

A proposal made no change. A separate human-side approval code and fingerprint were required before the exact plan could execute. Approved actions received operation IDs and supported protected Undo. Expiry, tampering and late conflicts were rejected.

### v0.4 — Metadata-only real-folder inventory

Four additional tools introduced explicitly approved inventory roots. Cypher could inspect only metadata such as names, extensions, types, sizes and timestamps. It could not read file contents or change files.

This milestone also added extension-based graphic-design candidate detection and maintained traversal, link and scan-size limits.

### v0.5 — Dry-run graphic-file organizer

The broker reached sixteen narrow tools. Cypher could create a persistent, fingerprinted organization plan between an approved metadata-only source root and an approved planning destination.

Plans preserve filenames, refuse overwrite, detect source changes and destination conflicts, expire after a bounded review period, and can be reviewed and validated. Real-folder execution remains deliberately unavailable in v0.5: review approves the plan, not permission to move real files.

## 6. Resident Windows assistant

The v0.6 resident-host series removed the need to open PowerShell and Hermes manually for normal conversations. Cypher now:

- starts automatically at Windows sign-in;
- runs as the signed-in standard user;
- keeps the supported Hermes gateway available;
- appears in the Windows notification area;
- opens with `Ctrl+Alt+Space` or its tray/widget controls;
- uses an authenticated loopback-only API;
- supports a single resident instance;
- keeps recent conversation context bounded;
- records metadata-only operational logs rather than prompts and answers;
- retains v0.6.3 as a cooperative rollback baseline.

## 7. Cypher Core Preview 5 — command-center foundation

Preview 5 established the working local command-center shell:

- draggable floating Cypher activation orb;
- movable and resizable Jarvis-inspired command center;
- optional always-on-top pin and maximized view;
- Auto, Fast, Deep and Vision routing controls;
- deterministic routing between Qwen, GPT-OSS and Gemma;
- live response streaming through Hermes Runs API;
- a real Stop button that propagates cancellation;
- New Chat and Copy controls;
- compact, non-personal Cypher identity instructions;
- truthful privacy, model-role and system-status panels;
- unfinished modules visibly labelled **Planned**;
- geometry-only UI state storage—never prompt or answer content;
- transactional installation and cooperative rollback.

The Preview 5 source passed **121 local tests**. Its clean upgrade package passed **79 included tests**, checksum verification and ZIP-integrity verification before release.

## 8. Cypher Core Preview 6 — reliable task foundation

Preview 6 converts the shell from a streaming chat interface into the first supervised task core:

- native Hermes approval cards with only **Approve once** and **Deny**;
- a deterministic task lifecycle that blocks unsupported completion claims;
- visible task phase and observed tool evidence;
- Stop verification against Hermes terminal state, including a visible unconfirmed state;
- deterministic human summaries for sandbox action approvals;
- stronger Windows path handling for device names, ADS syntax, extended paths, DOS aliases and reparse points;
- median, p95 and maximum latency reporting with three benchmark repetitions by default.

This milestone does not broaden Cypher's file roots or introduce unrestricted computer control.

Preview 6.1 corrected the Hermes capability feature name from the internal shorthand `run_approval` to the official `run_approval_response` contract.

Preview 6.2 adds capability honesty as a host-enforced boundary: Hermes `/v1/capabilities` and `/v1/toolsets` are inspected at startup, a conservative runtime contract is included with every run, direct capability questions bypass model improvisation, and unwired vision input is disabled. The source passed **138 local tests** before clean-package verification.

Preview 6.3 makes the resident experience hotkey-only: the floating desktop core is removed, tray interaction cannot reveal the command center, and `Ctrl+Alt+Space` opens a larger centered interface using a restrained 160 ms animation. A new layout-state version prevents older compact geometry from shrinking the upgraded interface.

Preview 7 adds durable task recovery without broadening authority:

- one atomic, schema-restricted metadata checkpoint for an active Hermes run;
- no persisted prompt, answer, conversation, filename, tool argument, approval content, credential or hidden reasoning;
- startup reconciliation with Hermes instead of guessing whether interrupted work succeeded;
- event-stream reconnection when the run remains active;
- truthful completed, cancelled, failed and recovery-required states;
- recovered approval only when Hermes returns current human-review details;
- exit and upgrade guards that prevent Cypher from knowingly orphaning active work;
- explicit human-side checkpoint inspection and confirmed emergency forgetting.

Preview 7.1.3 fixes the permissioned-operator dispatch boundary without expanding authority:

- exact visible MCP tools are called directly;
- deferred discovery is used only when an exact schema is absent, and returned wire names are
  preserved verbatim;
- one explicitly confirmed helper switches the bounded 22-tool Hermes catalog to direct schema
  loading, restarts the loopback gateway, verifies the server and rolls back the setting on failure;
- terminal failures produce a strict content-free receipt with only the run ID, selected role,
  bounded failure stage, timestamp and aggregate tool-event evidence; and
- `failure-status` exposes that safe metadata without reading provider logs or private task content.

The release candidate passes **142 local source safety tests**. Final milestone acceptance still requires compilation, executable self-test, installation and recovery validation on the target Windows PC.

### v0.8.1 — Windows Operator Preview 1

This functionality-first milestone adds the first genuine Windows application controls:

- enumerate visible top-level windows with bounded metadata;
- observe the foreground window;
- list exact executables registered by the user;
- launch a registered application without model-supplied command-line arguments;
- request focus for an existing window and verify the foreground result;
- seed common built-in Windows apps during setup; and
- keep window titles out of persistent audit logs.

It also repairs valid failure-receipt display under Windows PowerShell 5.1. The source passes **183
tests**. Target-PC acceptance of the native Win32 behavior remains required before calling this slice
complete.

## 9. Security and privacy boundary achieved

- No unrestricted shell or arbitrary code tool is exposed.
- No ambient access to the whole computer is granted.
- Cypher runs without administrator/system authority.
- UAC and consequential approvals remain human decisions.
- API keys are protected for the current Windows user with DPAPI.
- Hermes and Ollama communication is restricted to loopback.
- The resident host does not log prompts, answers, tool arguments or conversation history.
- Active-task recovery persists only whitelisted metadata and treats Hermes—not the checkpoint—as authoritative.
- External documents and web content cannot grant themselves authority.
- The capability broker, not the language model, enforces tool and folder boundaries.
- File operations refuse overwrite and are designed for preview, verification and reversal.
- Installer failures occur before switching the active resident host, and v0.6.3 remains available for rollback.

## 10. What Cypher can do today

Cypher can currently:

- start with Windows and remain hidden until `Ctrl+Alt+Space` is pressed;
- hold a local text conversation;
- route ordinary and difficult requests to different local models;
- stream responses and cancel active work;
- call the registered Hermes sandbox tools;
- safely list and read bounded sandbox text files;
- propose approval-gated, reversible sandbox file actions;
- inspect metadata from separately approved real folders;
- identify likely graphic assets by extension;
- create, retrieve, review and revalidate dry-run organization plans.
- preserve and reconcile one interrupted task without silently repeating it or claiming unverified success.
- in the v0.8 source candidate, propose and externally approve verified, reversible file operations
  inside explicitly scoped real folders.
- in the v0.8.1 source candidate, observe visible Windows app state, start a registered app, and
  request verified focus without arbitrary commands, typing, clicking, or screenshots.
- in the v0.8.6 source candidate, list safe actionable controls in one visible registered-app
  window and execute one approved Invoke, Toggle, Select, Expand, or Collapse action with fresh
  target revalidation and postcondition evidence.
- in the v0.8.7 source candidate, bind packaged windows to an exact `AppUserModelID` and set at
  most 500 printable single-line characters in one fresh safe Edit/Document control only after the
  human separately enables text entry for that exact registered application and approves once.

## 11. Current limitations

The following capabilities are **not yet completed**:

- native clarification cards inside the Cypher dashboard;
- target-PC acceptance and command-center integration of the v0.8 real-folder operator;
- target-PC acceptance of bounded UI Automation text entry;
- arbitrary pointer/keyboard input, clipboard pasting, coordinate automation, and unbounded control-level interaction;
- screenshot/image attachment through the current interface;
- persistent reviewed personal memory;
- read-only web research with citations;
- messaging or external-service actions;
- scheduled autonomous routines;
- microphone, speech-to-text, text-to-speech or wake-word activation;
- stable multi-agent orchestration across multiple specialist tasks;
- final WinUI 3 production shell.

## 12. Current acceptance gate

Core Preview 8.2 is the verified installed resident-shell baseline. The v0.8.7 source candidate passes
the complete regression suite. Its current acceptance gate is target-PC validation of
packaged-app identity and bounded UI Automation text entry:

1. run the transactional installer from a newly extracted release folder;
2. compile against the local .NET Framework UI Automation assemblies and pass the executable self-test;
3. migrate the Windows-app registry to version 2, confirm an exact Notepad `AppUserModelID` when
   Windows supplies one, and separately enable text entry for only the Notepad record;
4. inspect a blank Notepad document and confirm one fresh safe Edit/Document control advertises
   `set-text` without exposing the existing field value;
5. deny one fresh Set Text proposal and verify nothing changes;
6. refresh the IDs, approve one harmless Set Text action within 60 seconds, and verify delivery only
   to the exact revalidated control;
7. confirm expiry, replay, stale-control, unregistered-app, disabled-capability, password-field, and
   sensitive-app rejection.

This gate does not require changing Hermes, the 28-tool broker, model files, or existing folder
permissions. After acceptance, the next backend slice is a bounded multi-step application workflow
engine with explicit per-step authority, checkpoints, and verification. Citation-backed research remains a
separate network-capability milestone. Visual redesign and native voice remain deferred.

## 13. Longer-term direction

After the task engine is dependable, the accelerated planned order is:

1. permission-center backend and approval-gated operations across approved user folders;
2. read-only public web research plus supervised Windows observation and UI Automation control;
3. local knowledge, reviewed memory, schedules and bounded proactive routines;
4. backup, restore, permissions review and long-run reliability for a stable daily assistant;
5. push-to-talk, local speech and an optional local Cypher wake phrase after the backend is stable.

---

## 14. v0.8 Permissioned Local Operator Alpha 1

The accelerated Bundle A backend is now implemented in source. It adds explicit per-folder
capability records, bounded real-folder text reads, encrypted fingerprinted plans, external approval,
verified create/replace/copy/move/rename/mkdir/quarantine actions, multi-action rollback, protected
human-only undo and restart reconciliation. The current Hermes broker has 28 narrow tools; models still
cannot add permissions, approve, undo, run a shell, obtain administrator rights or permanently delete.

The complete 173-test source/regression suite passes and remains an installation gate. Alpha 1 still requires target-Windows DPAPI,
PowerShell, Hermes registration, interrupted-operation and protected-undo acceptance tests before it
becomes an installed verified milestone.

---

**Current summary:** We have progressed from a local Ollama chat model to a resident, model-routed
Windows assistant with a hotkey-only command center, authenticated Hermes orchestration, 28 bounded
broker tools, scoped real-folder permissions, encrypted approval-gated file plans, verified batch
execution, rollback, quarantine, human-only undo, cancellation, privacy-bounded restart recovery,
model-free Windows observation, approved registered-app launch/focus, and the first bounded approved
in-application UI Automation layer. The immediate gate is target-PC acceptance of Core Preview 8.3's
packaged-app identity and separately permissioned bounded text entry.

## 15. Core Preview 8 — deterministic read-only Windows observation

The first reliability slice of the Windows operator is now owned by Cypher's compiled resident host rather than by model-selected Hermes discovery. Four narrow natural-language intents are recognized before model routing: list registered applications, list titled visible windows, observe the titled foreground window, and report the observation boundary.

The route is bounded, read-only, and visible in the UI as **DIRECT · WINDOWS OBSERVATION**. It performs no Hermes run, model inference, command execution, screenshot, launch, focus change, typing, clicking, approval, or file modification. All ambiguous requests and every consequential action continue through the existing Hermes and capability-broker path.

This directly addresses the repeated target-PC failure in which Hermes exposed 28 broker tools but Qwen completed without selecting `tool_search` or `windows_list_apps`. Target-PC acceptance still requires compiling and installing the new host, then running the three read-only prompts documented in `CYPHER_CORE_PREVIEW_README.md`.

Preview 2 corrects a packaging-only failure in Preview 1: its PowerShell installer had been truncated before the shortcut save, host start, heartbeat verification, rollback fallback, and outer `finally` block. No target-PC installation occurred because PowerShell rejected the incomplete file during parsing. The replacement launcher now performs a native PowerShell parser preflight before executing the installer, and the regression suite requires the full transactional ending to be present.

## 16. Core Preview 8.1 — deterministic approved Windows control

The next Windows-operator slice is implemented in the resident host. Cypher now recognizes two exact actions before model routing: launch one human-registered application without arguments, or focus one currently visible titled window by the numeric ID returned from the read-only window list.

Both actions use a native in-memory approval lifecycle: prepare, display exact target evidence, approve once or deny, expire after 60 seconds, consume before execution, revalidate, execute, verify, and report. App approval binds the registry ID, display name, canonical executable path, size, timestamp and SHA-256. Window approval binds the handle, title, class and PID. Fingerprints are canonical SHA-256 values; a changed target, expired approval, replay, restart, or failed postcondition produces no success claim.

This is deliberately not general computer use. It accepts no app arguments or arbitrary executable path and performs no typing, clicking, screenshot, shell command, process kill, persistent approval, or unattended continuation. Ambiguous, multi-step and broader tasks continue through Hermes and the permissioned capability broker.

Source validation now includes the resident-host regression suite and the existing Windows-operator behavioral suite before the installer can switch the login shortcut. Target-PC acceptance must still compile the WPF host, pass its executable self-test, deny one launch, approve a fresh launch, approve an exact window focus, and confirm denial/expiry/replay behavior.

## 17. Core Preview 8.1.1 — focus routing correction

The first target-PC focus attempt exposed a routing problem rather than an execution problem. A focus-shaped request using `window ID` wording, the displayed row number, a stale handle, or the literal `<ID>` placeholder could miss the deterministic target lookup and fall through to Hermes. Hermes then failed before a tool started, producing a misleading generic error even though no focus action or approval had occurred.

Preview 8.1.1 keeps focus requests inside the resident host. It accepts `Focus window 123`, `Focus window ID 123`, and `Focus the window with ID: 123`. Missing, placeholder, row-number, and stale IDs are rejected locally with instructions to refresh the visible-window list and copy the exact value printed after `ID`. No model run starts for these malformed focus requests, and the approval and execution boundary is unchanged.

## 18. Core Preview 8.2 — bounded registered-app UI Automation

Preview 8.2 adds the first in-application action layer without introducing raw computer control.
Cypher can inspect exactly one currently visible window only when its owning executable matches a
human-registered application. It walks a bounded Windows UI Automation control tree and exposes only
non-password, non-edit, non-document elements that support Invoke, Toggle, SelectionItem, or
ExpandCollapse. Each result receives a short, session-fresh `uia-...` identifier and reports only
control metadata and supported actions; no value or text pattern is requested.

One exact action can then be proposed inside the compiled host. The approval card binds the registered
app, canonical executable metadata and SHA-256, window identity, control identity, action pattern,
expiry, and canonical plan fingerprint. Approval is single-use and in-memory. Immediately before
execution Cypher re-resolves the app, executable, window, control, and requested pattern. Toggle,
selection, expand, and collapse actions require a verifiable state transition; Invoke reports only
that Windows UI Automation delivered the request because downstream application effects cannot be
generically proved.

This preview deliberately excludes text entry, raw mouse or keyboard injection, coordinates,
screenshots, shell commands, password controls, edit/document controls, unregistered applications,
persistent approvals, multi-action macros, and unattended continuation. Sensitive Windows and
password-manager executables are blocked even if registration is attempted. The Linux-side source
suite verifies the deterministic boundary; the build is not an installed milestone until its Windows
installer compiles the host, runs the executable self-test, and a harmless registered-app acceptance
test confirms listing, denial, approval, execution, replay rejection, and expiry behavior.

## 19. Core Preview 8.3 — packaged-app identity and bounded text entry

Preview 8.3 extends the human-managed Windows application registry to a strict version-2 schema. A
record may contain an exact Windows `AppUserModelID` and an independent `allow_text_entry` Boolean.
Version-1 records migrate with both additions disabled. Built-in seeding may discover an exact
packaged identity, but it does not silently enable text entry; the human must use the dedicated
manager command and confirmation phrase for the exact app ID.

The resident host reads a top-level window's AppUserModelID through the Windows property store. A
registered window is accepted only when its executable or its nonempty packaged identity exactly
matches the record. This supports packaged applications without treating a shared host executable as
blanket authority. The identity and text-entry capability are included in the approval fingerprint
and revalidated immediately before an action.

For a separately text-enabled app, Cypher may expose `set-text` on one fresh Edit or Document control
only when Windows UI Automation reports a writable managed `ValuePattern`. The request accepts at
most 500 printable single-line characters. Password controls,
sensitive field labels and sensitive application processes are denied. The existing field value is
never read. The requested text lives only in the pending in-memory action; its length and SHA-256 are
bound into the approval, and denial, expiry, execution, or shutdown discards the raw payload.

Execution calls only `ValuePattern.SetValue` after exact
app/window/control/pattern revalidation. It does not use SendKeys, raw keyboard or mouse input,
clipboard automation, coordinates, screenshots, shell commands, or action chains. Because Windows UI
Automation cannot generically prove an app's later business effect, Cypher reports only that the exact
control accepted the value call without an exception.

All 210 source regression tests currently pass. The build remains a candidate until the target
Windows PC compiles and self-tests the host, migrates the registry, separately enables Notepad text
entry, and passes denial, fresh approval, execution, expiry, replay, stale-control, sensitive-field,
and disabled-capability acceptance checks.

## 20. Core Preview 8.3.2 — packaged identity resolver correction

The first packaged-Notepad acceptance isolated a resolver-ordering defect. Window enumeration worked,
but actionable-control inspection attempted to read the live package process image before considering
the exact AppUserModelID already registered for Notepad. Windows may protect or relocate that package
executable, so the observation failed before UI Automation began.

Fix 2 follows the Windows identity contract. It reads the explicit window AppUserModelID first and,
when absent, queries the process AppUserModelID with `PROCESS_QUERY_LIMITED_INFORMATION`. An exact
nonempty AUMID match is resolved before live image inspection. The exact executable path remains the
only fallback for ordinary desktop apps, so this correction does not turn a shared host process into
ambient app authority.

Direct observation failures now include a small safe diagnostic code while continuing to suppress
exception text, paths, prompts, control arguments, and credentials. Target-PC acceptance must confirm
that the current Notepad window now lists controls, then proceed with a fresh `set-text` denial and
one-time approval test.

## 21. Core Preview 8.4.1 — natural registered-app write workflow

Preview 8.4.1 removes the manual window-ID and control-ID steps from the first useful Windows workflow.
The resident host now recognizes `Open <registered app> and write: <text>` before model routing. It
requires an exact human-registered application with separately enabled text-entry authority and a
bounded printable single-line payload of at most 500 characters.

Preparation resolves either exactly one existing app window and one safe writable editor, or binds a
deterministic policy that may launch the exact registered executable without arguments if no matching
window exists. More than one matching app window or more than one eligible editor is rejected. One
native approval binds the app identity, executable metadata/hash, selection policy, resolved
window/control identity when available, text length/hash, action and expiry. Execution consumes the
approval, revalidates every bound field, resolves exactly one editor, and calls only the managed
Windows UI Automation `ValuePattern.SetValue` operation.

The route remains one bounded effect rather than arbitrary multi-step automation. It never reads the
existing field, uses raw mouse/keyboard input, accesses the clipboard, captures the screen, invokes a
shell, accepts an unregistered app, or creates a lasting permission. The previous ID-based inspection
and Set Text routes remain available for diagnosis and precise manual control.

Fix 1 corrects packaged Notepad revalidation after native approval. A refreshed window title remains
reviewed and fingerprinted context but is not treated as stable live identity. Execution still requires
the exact HWND, PID, class, registered app identity, executable and editor identity before Set Text.

All 212 local source regression tests pass. This build remains a source candidate until the target
Windows PC compiles and self-tests the resident host and passes denial, approval, exact-text,
one-time-use, and ambiguity acceptance checks with a disposable Notepad document.

## 22. Core Preview 8.5.0 — ordered Windows workflow candidate

The user's 26 August screenshot shows the existing-Notepad path of 8.4.1 working: the requested text
is visible and Cypher reports delivery through ValuePattern with one consumed approval. This is the
accepted evidence for that path; it is not evidence of a closed-app launch or of the new workflow engine.

The next implementation adds an explicit `Workflow:` recipe with at most six expanded steps across
three registered apps: Open, Write in, Focus, Minimize, Restore. All lines are parsed before approval;
unknown steps reject the whole plan. A complete native preview shows the text and ordered targets.
An atomic one-time approval binds the plan and expires after 60 seconds.

Execution revalidates the registered executable/app and exact window per step, reuses the existing
bounded text-entry implementation, persists counts/state before mutation, and requires a receipt
before advancing. A changed or ambiguous target, failed verification, or failed checkpoint stops
later work. There is no automatic retry. Stop is cooperative at action boundaries, and an in-flight
native call cannot be forcibly cancelled.

Checkpoints contain only random workflow ID, counts, state, schema, and timestamps. Restart marks
RUNNING as INTERRUPTED without replaying anything. The user must inspect existing effects and approve
a new plan. No prompt, text, app identity, title, path, hash, or reusable approval is persisted by
the new checkpoint store.

Current verification: 217 Python tests discovered; 216 pass and the Windows-only native compiler
test is skipped in this Linux environment. Twenty-three native behavioral scenarios are included
and wired into the pre-install and compiled-host self-test gates; they have not run here. Real
Windows compile, denial/approval, exact visible text, multiple apps, Stop, ambiguity, and restart
acceptance remain pending. Do not declare this milestone complete from source checks alone.

See `MULTISTEP_WORKFLOW_SETUP.md` and `RELEASE_NOTES_MULTISTEP_WORKFLOW.md`. The next action is target-PC
acceptance of this bundle, not another UI redesign or a broader unattended authority grant.

## 23. Core Preview 8.5.1 — Stop availability patch candidate

This section supersedes the earlier pending-acceptance summary for the current stopping point.

### Live evidence collected on Core Preview 8.5.0

| Check | Evidence and status |
| --- | --- |
| Installation | User reported successful installation; screenshots show Core Preview 8.5.0 running. Full installer logs were not separately reviewed. |
| Launch, write, minimize | 3/3 execution report, including an actual Notepad launch, followed by a screenshot with the exact requested text. |
| Two-app workflow | 4/4 execution report for Notepad and Calculator, followed by visible exact Notepad text. |
| Deny | DENIED report with no action; user confirmed the visible Notepad window stayed unchanged. |
| Minimize, Restore, Focus | 3/3 report; user explicitly confirmed all actions occurred as requested. |
| Ambiguous windows | AMBIGUOUS_WINDOWS rejection before approval when two Notepad windows were used. |
| Restart checkpoint | Post-restart status screenshot shows COMPLETED, 1/1. The user has not explicitly confirmed the separate no-replay window observation. |
| Stop before approval | CANCELLED report: workflow cancelled before approval, no action ran. |
| Stop during execution | Not established. One attempt failed at Calculator after 2/6 verified steps with AMBIGUOUS_WINDOWS. A Notepad-only run completed 6/6 without a cancellation result. |

### Current implementation

The v0.8.9.1 patch provides a two-second cancellable Stop window after consuming approval and before
any app action. The worker waits on the cancellation token while the WPF UI stays available. App and
window identities are revalidated after this window. Progress dispatch yields to pending input and
does not overwrite a STOPPING state. No new action, permission, app-selection exception, or replay
path is added. The Calculator ambiguity failure remains unresolved and is not bypassed.

Validation completed here: 218 Python tests discovered, 217 passed, one Windows compiler test skipped;
lexical delimiter checks passed for all five C# files. Two native behavior scenarios were added to
the existing harness for approval-stage cancellation and delayed execution. They must compile and
run on Windows; no native success is claimed from Linux source checks.

**Next user action:** install the new bundle from a separate folder, confirm Core Preview 8.5.1,
then follow `STOP_FIX_SETUP.md`. The first expected result is CANCELLED 0/2 during ARMING with zero
started actions and an unchanged Notepad window. This verifies Stop after approval before execution;
it does not prove cancellation of a synchronous native call already in flight. The patch itself is
not yet accepted on the target PC. Retain v0.8.9.0 for reinstall rollback.

## 24. Core Preview 8.5.2 — fast execution and cancellable observation

This section supersedes section 23's pending 8.5.1 acceptance status and next action.

### Confirmed since the previous package

- The user installed Core Preview 8.5.1 and supplied a CANCELLED 0/2 result with STOP_REQUESTED after approval during its arming window.
- The subsequent screenshot reports COMPLETED 2/2 for Notepad minimize/restore. The user then explicitly confirmed "all working".
- These complete the basic 8.5.1 checks. They do not prove cancellation inside a synchronous native call or resolve Calculator ambiguity.
- The user requested the next milestone and removal of the arming pause from routine use: fast tasks should not be slowed just to make a test easier.

### New candidate

v0.8.9.2 removes the two-second production pause and all ARMING UI states while retaining one-time full-plan approval. It makes launch/editor/window/focus polling wake on cancellation and respect the remaining execution budget. A workflow text write checks cancellation after app/control validation immediately before SetValue. When Stop arrives before an executor is entered, the final started count no longer labels that unentered step as attempted. Once a native step has begun, any missing receipt remains explicitly unverified.

The existing input-priority-friendly progress dispatch is retained. Stop does not force interruption of an in-flight Windows or UI Automation call, kill a process, undo changes, or grant a lasting permission. A fully verified run may correctly finish before a human can click Stop.

Calculator ambiguity is unresolved. On AMBIGUOUS_WINDOWS, the new build reports the registered app, match count, and up to five bounded window metadata rows, including class, owner HWND, and DWM cloak state. These fields help distinguish actual extra windows from hidden or hosted candidates, but they are diagnostic only: no candidate is ignored or silently substituted. Titles/document text are omitted from these rows and checkpoint storage remains unchanged.

### Verification and next action

The Linux source suite discovers 221 tests: 220 pass and one Windows-only compiler test is skipped. The native behavioral harness now contains 30 cases, including immediate public-runner execution, cancellation after one verified action while another simulated action is waiting, conservative partial results, budget-limited waits, late Stop, and bounded diagnostic formatting. Native cases are included for the Windows installer; they were not executed here.

**Next user action:** install from a new folder, confirm Core Preview 8.5.2, and follow FAST_WORKFLOW_SETUP.md. Check one normal four-step Notepad workflow with no countdown, then the short Calculator workflow. Share Calculator's diagnostic if ambiguity remains. No racing the Stop button or repeating the historical acceptance sequence is required. Retain v0.8.9.1 for reinstall rollback.

Further limits remain: native in-flight interruption is unsupported, live mid-execution cancellation is not yet independently observed, and crash-recovery/no-replay window behavior still needs separate live acceptance before a stable release. Voice, vision, and durable chat memory are not added by this release.

## 25. Core Preview 8.5.3 — hosted window pairing candidate

This section supersedes section 24's next action. The artificial arming delay stays removed, as requested by the user.

### New evidence

- Windows reported an empty ZIP during the first 8.5.2 extraction attempt. A fresh-path plain ZIP replacement was byte-verified after saving, and the user subsequently reached Core Preview 8.5.2. The reason for the original delivery/extraction failure is not established.
- The 8.5.2 Notepad screenshot reports COMPLETED 4/4 for reuse, text delivery, minimize and restore. The exact visible editor text and lack of countdown were not independently captured in that screenshot.
- The subsequent Calculator test failed at 0/2 verified after step 1 was entered. The diagnostic shows a shell-cloaked CoreWindow (HWND 2492882, PID 27408) alongside a minimized, uncloaked ApplicationFrameWindow (HWND 9766660, PID 24232). Both owner handles are zero. Step 1 may have changed Calculator; it was not verified.

### Candidate correction

Before approving an existing restored hosted app, Cypher can now prove that an exact content HWND/PID is a descendant of the exact registered frame. The immutable pair is bound to the approval. An explicitly approved launch can derive the runtime relationship from its uniquely observed frame. During subsequent observations, only that exact companion may be excluded when reattached or detached with the specific shell-cloaked shape. Unknown companions and actual extra app windows remain failures. Actions never substitute a content window for the bound frame.

The pair exists only in the current plan's memory. An already-minimized app may still reject at fresh preparation because its relationship has not been proved; manually restore it first. No blanket hidden/cloaked-window filter, new permission, automatic retry, arming delay or persistent pair cache is introduced.

### Verification and next action

The Linux suite discovers 223 tests: 222 pass and one Windows-only compiler test is skipped. The existing native harness has 40 scenarios, including ten new matching/proof scenarios. These are included for Windows compilation/execution and do not establish target-PC success from source checks alone.

**Next user action:** install v0.8.9.3 from a new folder, confirm Core Preview 8.5.3, manually restore exactly one Calculator window, then approve Minimize Calculator / Restore Calculator. Expected: COMPLETED 2/2 and the same window restored. See HOSTED_WINDOW_FIX_SETUP.md. Retain v0.8.9.2 for reinstall rollback. Do not repeat all historical tests or race the Stop button.

Target-PC acceptance of this correction is pending. Broader live mid-execution cancellation and crash/no-replay observations remain separate gaps. The broader milestone is not declared production-ready.


## 26. Core Preview 9.0.0 — public source research candidate

This section supersedes section 25's pending focused Calculator acceptance and next action.

### Accepted evidence and retained decision

The user supplied the Core Preview 8.5.3 screenshot with COMPLETED 2/2 for Calculator minimize/restore
and explicitly confirmed that the visible behavior occurred. That focused path is accepted on the
target PC. It does not establish broad cancellation, crash/no-replay, or production readiness.
The user's instruction to remove the artificial arming pause remains in force; no countdown or
extra action approval stage is reintroduced.

### Current implementation

The user asked to proceed with the next milestone. Bundle B now has an explicit `Research:` route:
one to five public HTTPS source URLs and a question, a separate bounded standard-library worker,
local installed-model synthesis without tools, and checked source references and exact matching
passages. Public-address pinning/TLS, robots rules, redirects, size/time limits and no login/scripts
constrain retrieval. The question is not sent to a search provider. Automatic search is not connected.
The sources stay outside Hermes/action history; no app/file action or reusable approval can be
created by the research result. Matching citations are provenance, not semantic fact verification.

Research worker lifetime is owned by the native host with a Windows job, bounded protocol and
confirmed-exit gating. A pre-start Stop cannot start work later. The process and streams are not
released while the runner is still unwinding. No other app or the Ollama service is killed; an
already-submitted model call may take time to stop. Process separation is not an OS sandbox.

### Verification and next action

273 Python tests discovered: 272 passed, one Windows compiler test skipped. The 50 research tests
include real isolated Python invalid-input rejection as well as network/model fixtures. Existing
8.5.3 workflow engine/adapter/harness files are retained. The full Windows installer compiles the host,
runs retained and new native protocol tests, then launches an actual owned worker with a local URL
that must be rejected before any network access. It separately checks rejection of startup after Stop.
These native gates have not run in Linux. No live page fetch plus real local-model synthesis is
claimed from fixtures.

Next: install v0.9.0.0 from a new folder using `INSTALL_CYPHER_RESEARCH_PREVIEW.cmd`, confirm Core
Preview 9.0.0 and run the single Python-documentation research check in `RESEARCH_PREVIEW_SETUP.md`.
Keep accepted v0.8.9.3 for reinstall rollback. Share the answer/source passage or the exact diagnostic;
there is no need to repeat historical Windows acceptance or race a Stop button.

Automatic search, stronger OS containment, repeated-run latency/VRAM checks, live research Stop/exit
and broader crash-recovery acceptance remain open. Voice, vision, reviewed memory and schedules are
not included. This is a test candidate, not a declaration that the full research milestone is stable.


## 27. Core Preview 9.0.0 — Encoding Fix 1

The first research installation stopped before resident-host replacement. The user's screenshot
shows two errors in the 50 research tests: a UTF-8 worker source was read with the Windows CP1252
default. The original package reproduced the two CP1252 decode errors, including the exact worker
byte offset 29825 and the corresponding host-source failure at offset 190634.

All six new research-test source reads now specify UTF-8, as the older source checks already did.
The subprocess protocol test also specifies UTF-8. One regression reruns the actual host/worker
source checks under a CP1252 default; it fails before this correction and passes after it.
No gate is bypassed. Worker/host code, installer logic, models, approvals and Stop are unchanged.

Verification: 274 source tests discovered, 273 passed and one Windows compiler test skipped.
The full suite also passes with Path.read_text defaulted to CP1252. All 51 research tests pass with
default-encoding warnings treated as errors. Native Windows compilation, owned-worker runtime
checks and live website/Ollama acceptance are still pending; the simulation does not replace them.

Next: download the corrected ZIP again, extract the Cypher-9.0.0-EncodingFix1 folder, run
INSTALL_CYPHER_RESEARCH_PREVIEW.cmd normally, and confirm Core Preview 9.0.0 after installation.
Keep 8.5.3 for rollback. Continue with the single existing research check; do not change locale,
permissions or skip safety tests. See RELEASE_NOTES_ENCODING_FIX_1.md.


## 28. Core Preview 9.0.1 — reader-assigned research citations

The user installed Encoding Fix 1 successfully. Public page retrieval passed. The
first model diagnostic found the local Ollama endpoint unavailable; starting Ollama
resolved that blocker. A later run confirmed Ollama 0.32.13 and completed Fast-model
generation. Citation Check 2 then identified QUOTE_NOT_EXACT at finding 2/support 1:
147 characters, with case/spacing/backtick difference flags all false. No rejected
answer text or private logs were collected.

The 9.0.1 candidate replaces model-written quotes with selection of reader-assigned
passage IDs. Exact source slices are resolved locally and the original quotation
validator remains unchanged. Request-specific enum/schema constraints, independent
ID/source/offset checks and strict JSON handling preserve rejection of fabricated
references. Schema/ID failures now have fixed diagnostic codes in the visible report.

Verification: 288 tests discovered, 287 passed, one Windows compiler skip. All 65
research tests pass with EncodingWarning as an error. The original network,
extraction, local transport and exact-quotation validator have unchanged ASTs.
Windows workflow implementation and native research lifetime code remain unchanged;
the native host's only research integration change is its worker hash pin.

Next: install this 9.0.1 candidate in a fresh folder and repeat the one-page Python
documentation request in the Cypher UI. Real model success for the correction and
native installation remain target-PC gates. Do not rerun the 9.0.0-pinned standalone
diagnostic against the new worker. No arming pause, extra generation, permission
expansion, model download, automatic search or broad retest is added.


## 29. Core Preview 9.0.2 — research clarity and two-source check

This section supersedes section 28's pending focused 9.0.1 acceptance and next action.

The user supplied a 9.0.1 screenshot showing RESEARCH COMPLETED with one source and three findings.
The answer to the can_fetch question matched the source's main definition; that focused
one-source research path is accepted. The third finding repeated the first and the visible 25-word
excerpt began at preceding setup methods. This is not broad semantic-citation or research acceptance.

The user authorized this follow-up. The 9.0.2 candidate requests distinct findings and only material
limitations, removes exact text/evidence duplicates after complete validation, and chooses a relevant
sentence-prefix preview solely from the selected evidence. Findings and preview references are
numbered. Exact slices, source identity and quotation/summary bounds remain; the display heuristic
cannot establish entailment and the duplicate filter does not merge paraphrases or distinct evidence.

309 tests discovered: 308 passed, one Windows compiler skip. The 86 research tests include 21 new
clarity/comparison cases and full two-source fixture paths with one local generation per request.
Native worker lifetime and Windows action implementation remain unchanged; no arming delay or extra
approval stage returns. No new network authority, model download, paid service or durable report.

Next: install 9.0.2 in a new folder and run the single two-source comparison in RESEARCH_PREVIEW_SETUP.md.
Check the difference between can_fetch and urlopen, both citation identities, useful excerpt previews,
and absence of restated findings. The actual model wording and new native installation remain target-PC
gates. Keep working 9.0.1 for rollback. Broader Stop/exit, crash/no-replay and repeated-resource
acceptance remain separate; the next major capability is not being declared complete here.


## 30. Core Preview 9.0.3 — explanatory evidence and qualified answers

This section supersedes section 29's pending focused 9.0.2 execution check and next action.

The user's 9.0.2 screenshot shows RESEARCH COMPLETED, two sources and two distinct findings.
The comparison pipeline ran, but the previews showed a module introduction and a signature.
The urlopen finding also omitted the response-object distinction and implied HTTP-only scope.
The screenshot does not reveal the complete private draft; synthetic fixtures reproduce the
structural failure class without claiming a live replay.

The authorized 9.0.3 correction preserves paragraph/definition/code boundaries and nearby visible
definition context. Signatures/headings/source-path records become labels, not selectable support.
Passages retain exact source offsets, bounded lengths and fragment markers. The model still makes
one generation; new instructions preserve return types, conditions and protocol scope and keep
absence claims scoped to read excerpts. Previews prefer already-selected explanations without
substituting unselected text. This is not a new semantic validator or a hardcoded API answer.

333 tests discovered: 332 passed, one Windows compiler skip. All 110 research tests pass, including
24 new structure/context/qualification-evidence regressions. The full CP1252-default suite and
EncodingWarning-as-error research suite pass. Network policy, local transport and exact-quotation
validation retain their ASTs. Workflow source files are unchanged, native research lifetime changes
only in the worker hash, and other host/installer edits are version labels. No arming delay returns.

Next: keep 9.0.2 for rollback, install 9.0.3 normally in a fresh folder, and repeat the same two-source
question in RESEARCH_PREVIEW_SETUP.md. Check explanatory excerpts and a qualified response-object
answer, plus the existing distinction, citation and non-repetition checks. Real-model wording and
native installation remain target-PC gates. Broader research Stop/exit, rollback, repeated-run
latency/VRAM and stronger containment remain unverified; automatic search and other Bundle B
capabilities are still deferred.


## 31. Core Preview 9.0.4 — focused qualification evidence

This section supersedes section 30's pending 9.0.3 answer-quality check and next action.

The user installed 9.0.3 successfully. One request returned `MODEL_UNAVAILABLE`; the unchanged retry
completed with two sources and two findings. The new previews passed: each page showed relevant
definition text instead of a module introduction or signature. The answer still described `urlopen`
as an actual network operation, emphasized HTTP/HTTPS without its returned-response and broader URL
cases, and added an error-handling limitation the question did not request. No raw draft was collected.

The authorized 9.0.4 correction uses the reader's already-validated definition contexts to create
bounded, non-citable focus groups for identifier names in the question. Direct description,
return/result and contrasting case-scope passages are placed first in the same evidence payload;
all cited IDs retain the existing source/offset/structure/exact-text validation. Direct questions
without explicit limitation intent require no limitations, and the worker validates before omitting
a valid unrequested tangent. Malformed output still fails closed. Return/result findings can prefer
selected return/result evidence in the source preview. This is not an entailment checker or a
hardcoded Python-API answer.

340 tests were discovered: 339 passed and one Windows compiler test was skipped. All 117 research
tests pass, including seven new focus, bounds, cue-authority, preview and limitation-intent cases.
The full CP1252-default suite and EncodingWarning-as-error research suite pass. There is still one
model generation, no automatic retry, arming delay, semantic repair, permission expansion or new
action. Workflow source remains unchanged; native integration changes only version labels and the
pinned worker hash.

Next: keep 9.0.3 for rollback, install 9.0.4 normally in a fresh folder, and repeat the exact same
two-source question. Check that `can_fetch` remains a parsed-rules permission decision, while
`urlopen` opens a URL/request and returns a response object without treating every supported case as
a network operation or HTTP/HTTPS as the complete scope. No unrelated error-handling limitation
should appear. No workflow, Stop-race or model-installation retest is required. Real-model acceptance
of this wording remains pending; automatic search and other Bundle B capabilities remain deferred.


## 32. Core Preview 9.0.5 — fail-closed research scope guard

This section supersedes section 31's pending 9.0.4 answer-quality check and next action.

The user installed 9.0.4 successfully. The unchanged two-source request first returned
`MODEL_UNAVAILABLE`, then completed after a manual retry. The `can_fetch` finding was useful, both
previews remained explanatory, and the unrequested limitation was gone. The `urlopen` finding still
promoted an HTTP-specific passage to general behavior and added unsupported "actual network request"
wording. Focus ordering and prompt guidance alone therefore did not close the visible failure class.

The authorized 9.0.5 correction adds a deterministic post-resolution guard for named-definition
findings. Selected case-scope evidence requires an explicit condition marker. Unsupported scope
intensifiers and substantive words of seven or more characters must occur in the question or selected
passages, apart from a fixed neutral comparison vocabulary. Failure withholds the entire draft as
`CLAIM_SCOPE_UNSUPPORTED` and retains source metadata; it never retries, repairs, salvages other
claims, or substitutes evidence. The same one-call prompt now prefers direct plus general-return
evidence for general claims and uses temperature zero. This is lexical fail-closed filtering, not
semantic entailment verification or a hardcoded Python answer.

346 tests were discovered: 345 passed and one Windows compiler test was skipped. All 123 research
tests pass, including the exact visible overgeneralization, valid general/scoped cases, unsupported
mechanism/intensifier terms, non-definition prose, and complete metadata-only failure rendering. The
full CP1252-default suite and EncodingWarning-as-error research suite pass. Existing Windows workflow
source remains unchanged; native integration changes only version labels and the pinned worker hash.
There is no additional model call, automatic retry, arming delay, approval, Stop stage, permission
expansion, or new action.

Next: keep 9.0.4 for rollback, install 9.0.5 normally in a fresh folder, and repeat the unchanged
two-source question once. A useful complete answer should preserve the documented distinction and
scope; otherwise the observed error class must be withheld with `CLAIM_SCOPE_UNSUPPORTED`, two source
records and zero findings. No workflow, Stop-race or model-installation retest is required. Real-model
acceptance remains pending; automatic search and other Bundle B capabilities remain deferred.


## 33. Core Preview 9.0.6 — fail-closed research desktop isolation

The user's 9.0.5 screenshot accepted section 32's protective path: the model produced unsupported
scope wording, Cypher displayed `CLAIM_SCOPE_UNSUPPORTED`, retained both source records and displayed
zero findings. The user then authorized the next milestone and reiterated that fast work should not
gain an artificial warning, arming pause or extra Stop step.

The next Bundle B slice therefore hardens containment before expanding automatic source discovery.
The research job now sets all eight documented Windows UI restriction flags: foreign USER handles
and hooks, clipboard read/write, system parameters, display settings, global atoms, desktop
creation/switching and Windows exit calls. The host immediately queries the job and requires the
exact mask before `Process.Start`; any set/query failure or weakened value fails closed as
`WORKER_UI_ISOLATION_UNAVAILABLE`. The existing one-process, kill-on-close and 512 MiB limits remain,
and request JSON is still withheld until after job assignment.

This is desktop-surface isolation, not AppContainer. The worker retains the standard-user token and
the deterministic HTTPS/loopback policy; filesystem, registry and network sandboxing are not claimed.
Microsoft's experimental composable sandbox API is not adopted as a stable dependency.

347 tests were discovered: 346 passed and one Windows compiler test was skipped. All 124 research
tests pass, including the exact restriction constants, set/read-back ordering, fail-closed diagnostic
and absence of a USER-handle grant escape. CP1252-default and EncodingWarning-as-error checks pass.
Windows workflow sources remain byte-identical to 9.0.5. No automatic search, provider, extra model
call, retry, approval, arming delay, Stop stage, new permission or workflow action is introduced.

Next: keep 9.0.5 for rollback, install 9.0.6 normally from a new folder and confirm the successful
installer result plus **CORE PREVIEW 9.0.6**. The installer's offline worker start sets and reads back
the exact native restriction mask, so no live website, local-model, workflow, approval or Stop-race
retest is required for this hardening-only slice. AppContainer/filesystem/network containment and
automatic source discovery remain separate future Bundle B work.

## 34. Core Preview 9.1.0 — bounded English Wikipedia discovery

The user accepted 9.0.6's native installation gate and authorized the next milestone while retaining
the preference that fast work must not gain an artificial warning, arming delay or extra Stop step.
Core Preview 9.1.0 therefore adds the smallest official-provider discovery route rather than a paid
search API or brittle HTML search-results scraper.

A `Research:` question with no URL lines makes one fixed GET to the English Wikipedia MediaWiki
Action API. Only the cleaned typed question is variable, bounded to 400 UTF-8 bytes. The response is
limited to 64 KiB and three namespace-0 records. Positive page ID and clean title are required;
Cypher constructs each candidate URL locally on `en.wikipedia.org`. Snippets, provider URLs,
suggestions and scores are ignored. Candidate and robots redirects cannot leave that provider host.

Every candidate article still passes the existing public-address, pinned-TLS, robots, redirect,
content-type, body, extraction, passage, citation and scope checks. A question plus one to five
explicit public HTTPS URL lines bypasses discovery and keeps the question local. There is no API key,
paid provider, pagination, retry, fallback, extra local-model generation, approval card, arming pause,
new tool or Windows action.

The discovery route visibly states that Wikimedia receives the typed question and ordinary network
metadata. Chat history, local files, durable memory, application state, prior research, the model
prompt and answer are not forwarded. This is English Wikipedia discovery, not general web/current-
news search. The accepted 9.0.6 worker desktop restriction mask and standard-user limitations remain.

The focused research suite passes 134 tests. The complete suite discovers 357 tests: 356 pass and
the one expected Windows-only compiler test is skipped on Linux. The same complete suite passes with
CP1252 as the default `Path.read_text()` encoding, the focused suite passes with Python's default-
encoding warnings treated as errors, and all four retained Windows workflow sources remain byte-
identical to 9.0.6.

The user installed 9.1.0 successfully and its question-only target-PC result accepted the live route:
the fixed provider returned candidates, two Wikipedia sources were read, and four cited findings were
displayed. A third discovered source was rejected as `CONTENT_LIMIT`; that did not invalidate the
provider gate but exposed unnecessary work and lost usable bounded evidence.

## 35. Core Preview 9.1.1 — bounded Wikipedia reader reliability

Core Preview 9.1.1 keeps at most three discovery candidates in explicit provider relevance order and
attempts them serially only until two usable sources exist. If an earlier candidate fails or resolves
to a duplicate, the next candidate may fill the target. Once two sources are usable, lower-ranked
candidates are not fetched. Explicit one-to-five-URL requests continue to attempt every selected URL.

Readable HTML/plain-text responses larger than 1 MiB now contribute only their bounded prefix. At
most one extra byte is read when an unannounced response length requires overflow detection; the
remainder is not consumed. The source report discloses the truncation and hashes only fetched bytes.
Discovery JSON remains a strict 64 KiB object and truncated robots policy remains unavailable, never
permission.

The change adds no search request, provider, retry, model call, action, permission, approval, arming
delay or Stop stage. The focused research suite passes 139 tests. The complete suite discovers 362
tests: 361 pass and the expected Windows-only compiler test is skipped on Linux. CP1252-default and
EncodingWarning-as-error checks pass. The four retained Windows workflow sources are byte-identical
to accepted 9.1.0.

The user subsequently installed 9.1.1 and accepted its live question-only result: two Wikipedia
sources were read, four cited findings were displayed, provider ordering was disclosed, and the
third lower-ranked candidate was not fetched after the target was met. This is now the rollback
baseline for subsequent research work.

## 36. Core Preview 9.2.0 — bounded academic research

Core Preview 9.2.0 adds a separate `Research papers:` route. One fixed, keyless official OpenAlex
Works request contains only the bounded typed question, fixed English/non-retracted/has-abstract
filters, a three-record limit and an exact selected-field list. No API key, authorization header,
billing credential, provider fallback, retry, pagination, PDF, or full-text request is configured.

Returned records are handled in provider order. At most three are validated and at most two eligible
reconstructed abstracts enter one existing-local-model synthesis call. Strict checks cover response
type/size, duplicate JSON fields, exact record schema, canonical OpenAlex Work IDs, language,
retraction status, token count, and unique contiguous inverted-index positions. Titles remain visible
source labels, but titles, identifiers, rank/relevance score, citation counts, publication metadata,
and response metadata are never supplied as model evidence.

The retained passage catalog, model schema, exact source/offset binding, quotation, citation, and
claim-scope checks apply before display. Academic citations link the public OpenAlex Work record and
hash the reconstructed abstract text. The accepted Wikipedia and explicit-URL paths are unchanged.
Research still has no action authority, saved chat/task history, approval card, or arming countdown;
Stop is available while the owned worker runs.

The live target-PC gate is one Auto request documented in `RESEARCH_PREVIEW_SETUP.md`. Repeated-run
latency and VRAM remain target-PC observations; architecture tests enforce the latency-critical one
provider request, zero paper-page fetches, one synthesis call, no retry, and two-abstract maximum.

Pre-package verification: all 151 focused research tests pass; the complete suite discovers 374
tests, with 373 passing and the expected native Windows compiler test skipped on Linux. The
EncodingWarning-as-error research run and bytecode compilation also pass. Native compilation,
installer self-tests, and live provider/model latency remain target-PC gates.

The user installed 9.2.0 and its focused request entered the correct academic route but returned
`PAPERS_UNAVAILABLE` before reading any source. The exact provider query and response schema were
independently validated, leaving connection/address selection or an undifferentiated HTTP status as
the unresolved target-PC boundary.

## 37. Core Preview 9.2.1 — OpenAlex connectivity reliability

Core Preview 9.2.1 retains the one-request academic contract while allowing up to four addresses
from the single fully validated public-IPv4 DNS result to be tried during TCP/TLS establishment.
This happens only before the HTTP request is sent. A certificate-verification failure stops
immediately, and a request that has begun is never retried.

The worker now distinguishes pre-request connection exhaustion, post-send network interruption,
anonymous rate limiting, access denial, provider 5xx failure, and other unsuccessful statuses. It
still has no credential, alternate provider, pagination, full-text/PDF fetch, extra model call,
approval card, or arming countdown. Stop remains available only while the worker is running.

Three focused transport tests cover alternate-address establishment, fail-closed certificate
handling, and the no-post-send-retry invariant. The accepted Windows workflow sources remain
byte-identical. The focused research suite passes all 155 tests; the complete suite discovers 378,
with 377 passing and the expected native Windows compiler check skipped on Linux. The only live gate
is the unchanged target-PC paper prompt in the setup guide.

## 38. Core Preview 9.2.2 — bounded Crossref 503 fallback

The target-PC status check proved that 9.2.1 reached OpenAlex over validated public IPv4, completed
TLS, sent exactly one request, and received a well-formed HTTP 503 with `Retry-After: 60`. OpenAlex
reported that anonymous search was temporarily paused under load. The failure was therefore provider
availability, not installation, TLS, DNS selection, or local-model configuration.

The selected correction keeps OpenAlex primary. Only an exact OpenAlex HTTP 503 permits one
immediate keyless Crossref Works request containing the same bounded typed question. A rate limit,
other 5xx, access denial, invalid response, empty result, connection failure, or interrupted exchange
does not permit fallback. Neither request is retried, delayed, or repeated. There is no account, key,
payment, 60-second wait, extra warning, approval, arming countdown, or additional model call.

Crossref discovery requests at most three deposited-abstract journal-article records with an exact
field selection. Strict validation covers response size/type, duplicate JSON fields, top-level
schema, record fields, canonical DOI, title, type, optional language and score, and abstract markup.
Active/script-like markup contents are discarded; normalized deposited abstract text alone can
become evidence. Explicitly non-English records are skipped and absent language receives a
conservative English-text check. At most two abstracts enter the retained single local-model call.
Crossref titles, DOI identifiers, ranking, scores, and other metadata are excluded from model
evidence. The report links canonical DOI records, hashes the normalized abstract, identifies the
provider transition, and discloses that Crossref does not independently guarantee language or
retraction status.

The accepted research worker desktop restrictions, Stop behavior, metadata-only persistence,
Wikipedia and explicit-source routes, and Windows workflows remain unchanged. The one live gate is
the single Auto paper prompt in `RESEARCH_PREVIEW_SETUP.md`; no Stop, approval, or workflow retest is
required.

All 166 focused research tests pass. The complete suite discovers 389 tests: 388 pass and the one
native Windows compiler test is expectedly skipped in the Linux build environment.

## 39. Core Preview 9.2.3 — OpenAlex natural-question fix

The target-PC OpenAlex status check then returned HTTP 400 and supplied the decisive provider error:
the ordinary terminal `?` in the natural-language research question was treated as wildcard syntax,
while the default OpenAlex search is stemmed. This proved that installation, DNS, TLS, and request
delivery were working and that the question transport—not user setup—caused the rejection.

The worker now keeps the original cleaned question unchanged for the local-model synthesis and
derives a separate provider query by converting only ASCII `?` and `*` to spaces and collapsing
whitespace. OpenAlex receives that punctuation-safe copy. If the existing exact-503 transition is
entered, Crossref receives the same normalized terms. The route does not use `search.exact`, because
the request is a natural-language question rather than a literal no-stem or wildcard query. A
wildcard-only query fails before network access.

OpenAlex HTTP 400 now maps to the explicit `PAPERS_REQUEST_REJECTED` diagnostic and never triggers
Crossref. The one-request primary path, exact-503-only fallback, no-retry rule, single local-model
call, two-abstract ceiling, desktop restrictions, Stop behavior, and accepted Windows workflows are
unchanged. No account, API key, payment, wait, extra warning, approval, or arming countdown was added.

All 167 focused research tests pass. The complete suite discovers 390 tests: 389 pass and the one
native Windows compiler test is expectedly skipped in the Linux build environment. The user then
installed 9.2.3 and its unchanged focused request completed with two sources and three cited findings,
accepting the natural-question transport correction. That result also showed an indirect chain being
presented for a requested direct relationship, which motivates the next milestone.

## 40. Core Preview 9.2.4 — direct evidence relevance

The academic reader still makes one OpenAlex request and validates at most three returned records.
Instead of selecting the first two eligible abstracts solely by provider order, it now ranks their
abstract text locally against the unchanged original question and supplies the strongest at most two
to the existing single local-model call. Provider order breaks only exact local-score ties. Titles,
identifiers, provider ranking/scores, citation counts, and other metadata remain outside the score and
model evidence.

For recognized explicit two-concept relationship questions, the worker derives two literal term
groups locally. A relationship finding survives only when the finding and one cited sentence both
contain every term from both groups plus relationship wording. Recognized indirect or mediated
passages are withheld. If all draft findings fail, the report retains checked sources and returns
`DIRECT_EVIDENCE_MISSING`; if a direct finding survives, only rejected extras are omitted and counted.
This lexical rule does not infer synonyms, prove causality, or rank study quality.

The change adds no provider request, retry, fallback condition, model call, warning, approval, arming
countdown, fixed wait, action authority, persistence, Stop stage, or Windows workflow change. Five new
regressions cover direct third-record selection, same-passage directness, indirect-chain withholding,
mixed direct/indirect drafts, and same-call relationship concepts. All 172 focused research tests
pass. The complete suite discovers 395 tests: 394 pass and the one native Windows compiler test is
expectedly skipped in the Linux build environment. The one live gate is the same natural question in
`RESEARCH_PREVIEW_SETUP.md`; no Stop, approval, warning, or workflow retest is required.

## 41. Core Preview 9.2.5–9.2.6 — local runtime diagnosis and repair

Reducing model budgets in 9.2.5 did not resolve repeated `MODEL_UNAVAILABLE`. A separate local
checker identified Ollama not running. 9.2.6 restored the original synthesis budgets and added
installer-pinned Ollama autostart to the compiled host. The user installed it and the research run
reached one local synthesis, then withheld three indirect findings from two OpenAlex sources as
`DIRECT_EVIDENCE_MISSING`. This is accepted evidence of working synthesis/withholding in that
session, not an independent cold-boot, performance, or direct-source-quality test.

## 42. Core Preview 9.2.7 — academic discovery precision

The candidate preserves 9.2.6's runtime fix. Simple unambiguous relationship questions use two
normalized literal concept phrases joined by fixed OpenAlex Boolean AND. The same request accepts
up to eight records under the existing body/time limits and supplies at most two locally ranked
abstracts to one generation. Meaningful phrase words/numbers are preserved; ambiguous or qualified
forms retain the existing query. All records validate, even unselected ones.

Exact-503-only Crossref fallback remains. It receives provider-neutral terms; its local ranking now
retains the original question. The report exposes a memory-only query plan and bounded unselected
record count. No new provider, key, payment, model, generation, pagination, retry, warning, approval,
countdown, fixed wait, action authority, or content persistence is added.

184 focused tests pass; the full suite ran 408 tests, with 407 passing and one Windows compiler test
skipped on Linux. Live 9.2.7 relevance, provider/model behavior, native compilation, latency, VRAM,
and cold boot remain unverified here. Keep 9.2.6 for reinstall rollback. See
`RELEASE_NOTES_ACADEMIC_DISCOVERY_PRECISION.md` and `docs/CYPHER_NEXT_MILESTONES.md`.

## 43. Core Preview 9.2.8 — academic evidence preflight

The subsequent 9.2.7 screenshot confirms the focused query, two sources from eight eligible records,
and two withheld drafts. The duplicate image represents the same observed run. Discovery quality
remains open; the screenshot does not identify the exact rejected claim/support wording.

9.2.8 screens the selected sources' actual bounded passage catalog before academic synthesis with
the unchanged lexical relationship predicate. With zero passing passages, the worker makes no
Ollama API requests and reports `PAPERS_DIRECT_PASSAGE_MISSING`. If synthesis runs but its draft
fails, the report describes rejected wording/citations rather than blaming the abstracts. Per-source
counts stay memory-only. A native self-test covers partial completion without a synthesis event.

189 focused tests and 412 full-suite tests pass; one Windows compiler test is skipped on Linux.
Query, ranking, passage construction, model prompt/budgets, evidence guard, native runtime startup,
owned-worker lifetime and Windows permissions are preserved. This closes the reproduced preflight
and reporting defects, not the academic-discovery quality goal. Live 9.2.8 behavior and measured
time/VRAM effects remain unverified. See `RELEASE_NOTES_ACADEMIC_EVIDENCE_PREFLIGHT.md`.

## Dark Workspace — 8 September 2026

The user requested a darker minimalist interface alongside backend work. Preview 9.2.9 replaces
translucent decorative panels with a compact opaque WPF conversation window. The same research
worker is retained byte-for-byte. One source-level regression checks all control bindings and that
approval, Stop and recovery stay outside collapsed details. A native layout test is added to the
existing installer self-test before host replacement. Full suite: 413 passes, one Windows-only skip;
research: 189 passes. Design-reference images are not native screenshots. Windows DPI, appearance
and interaction await observation. See `RELEASE_NOTES_DARK_WORKSPACE.md`.

The observed 9.2.8 screenshot supports the preflight behavior only. The next retrieval gate compares
current AND queries with a documented proximity candidate across multiple questions, with abstract
support reviewed separately from lexical counts. No usable live comparison is available here yet;
production query and evidence rules are not changed. See `docs/ACADEMIC_DISCOVERY_EVALUATION.md`.

## Refined Workspace — 8 September 2026

At the user's request, 9.2.10 adds a Dribbble-informed graphite/violet palette, a type hierarchy,
a centered welcome view and three input-only prompt cards to the native host. Guidance moves into
Session details; full reports and action approvals remain. Geometry preferences, worker bytes,
startup and permissions are retained. Full suite: 414 passes and one Windows-only skip. A native
installer self-test covers starter behavior and welcome transitions in addition to small-window
layout. Real Windows appearance remains unverified. See `RELEASE_NOTES_REFINED_WORKSPACE.md`.
The source-discovery evaluation is still open and has not been replaced by this visual milestone.

## Observation Deadline Fix — 8 September 2026

The user's 9.2.10 installation passed all 189 Python research tests, then returned native self-test
126 before host replacement. That code checks a 25 ms workflow budget during a 10-second requested
observation wait; it is separate from the later WPF layout check. The screenshot does not distinguish
the assertion's missing-fault and elapsed-time branches.

9.2.11 corrects a concrete early-wake defect: observation waits keep their original monotonic
deadline, capped by the existing budget, and recheck Stop before waiting only the remainder.
The original wall-clock test is retained unchanged. Eight deterministic C# cases cover early wakes,
fixed interval, cancellation, expiry, late wake, fractional remainder and invalid intervals.
The refined UI and research worker are preserved. Target-PC installation and appearance remain
pending; this does not close the discovery-quality milestone. See
`RELEASE_NOTES_OBSERVATION_DEADLINE_FIX.md` for validation and limitations.

## 10 September 2026 — captured evidence adjudicated; 9.2.12 guard correction

The user installed 9.2.11 and supplied READY native UI evidence. The four-question comparison and
15 matching abstract captures are now available. Raw lexical counts overstated the candidate:
job-autonomy hits were an aim and an indirect proposal, phone-use outcomes did not link sleep to
memory, and an adolescent study reported a null correlation. The candidate also lost a direct
teacher social-support/stress result. Proximity is not promoted; production AND discovery stays.
9.2.12 corrects these reproduced guard defects and checks null-result wording consistency, without
claiming broad entailment or complete coverage. Native 9.2.12 installation is unverified here.
See `docs/ACADEMIC_EVIDENCE_REVIEW.md` (from the package root). Next research work must distinguish
retrieval misses, fragmentation and lexical false negatives using the existing captured evidence;
no repeat user diagnostic is needed. Containment and runtime measurements remain separate gates.

## 10 September 2026 — desktop integration bundle

The user opted out of Computer Use and will run one consolidated Windows acceptance session.
Development continues in the accessible Linux workspace. 9.3.0 connects the existing file engine
to the native human approval panel; no new framework or model call is involved. It adds an owned,
integrity-pinned file worker, cooperative Stop/rollback, reviewed recovery, bounded organization
and a local task receipt view. See RELEASE_NOTES_DESKTOP_BETA.md and DESKTOP_BETA_SETUP.md.
Research scope and the native visual system remain frozen; the file starter and task routing are
the relevant UI changes. The delivery reset supersedes earlier research-first sequencing.

## 9.4.0 — runtime readiness bundle

The user completed the 9.3.0 live file checks. Organization/undo operation:
`ec09e5a0-d335-455a-a715-5629e27af643`. A later Stop-Test folder proposal ended CANCELLED with no
file action. These results are retained; further file test repetitions are not requested.

9.4 adds local status and a short one-generation measurement in the native UI, plus clear reversal
and undo labels in file receipts. No Computer Use plugin is used. Runtime reports are memory-only,
use fixed loopback and never display generated text. Status makes no generation; benchmark checks
local weights and uses the selected installed model once. No cold/warm or peak VRAM claims are
made from snapshots. One consolidated runtime handoff is documented in RUNTIME_READINESS_SETUP.md.
