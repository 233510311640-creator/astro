# Cypher Development Summary

**Updated:** 26 September 2026  
**Current release:** Cypher 10.8.0 - Bounded Public Site Search  
**Platform:** Windows 11, local-first, standard-user execution

The 10.8.0 release adds bounded same-site GET search through one unambiguous static search
form. `Web: search URL : QUERY` sends only the explicitly typed query if the page passes
the form checks, then previews exact fetched-page excerpts. It cannot render JavaScript
matches. The 580-test suite, native checks, WPF layout and transactional install pass;
the installed preview is READY. A live Python documentation search read two pages.

The 10.7.0 release adds model-free static form inspection. `Web: forms URL` reports bounded
same-host form destinations, declared methods and named non-sensitive fields without values,
filling or submission. The 575-test suite, native and worker checks, WPF layout,
transactional install and live public-page inspection passed; installed 10.7.0 is READY.

The 10.6.0 release adds a model-free follow step. `Web: follow URL : NUMBER` refreshes one public
page's current bounded link map and reads only the selected same-host destination, returning exact
excerpts. It has no browser profile, scripts, forms, local model, file or Windows actions. The
desktop map now prints Read commands, and the system rail has a Follow Link starter. 10.5.0 is
retained for rollback. The full suite passes 571 checks with one existing platform skip. Native
compilation, four owned-worker checks, workspace rendering and transactional installation pass.
Installed 10.6.0 reports READY, and a live Wikipedia follow read two pages with four excerpts.

The 10.5.0 release added a model-free page-navigation map. `Web: links URL` reads one explicit public
HTTPS page in isolation and returns at most six visible eligible same-site HTTPS destinations without
opening them. A selected result is submitted through the existing exact browser command and
one-time approval. The complete 10.4.0 package remains for rollback.
Its full suite passed 566 checks with one existing platform skip. Installed 10.5.0 reported READY,
and a live Wikipedia map completed with six same-host links.

## Project direction

Cypher is a private Windows assistant opened with **Ctrl+Alt+Space**. It combines local AI models
with deterministic, narrowly scoped tools. Models may propose or explain work, but permissions,
validation, approvals and post-action checks remain outside the model.

The project is local by default. It does not require a paid inference API, does not grant ambient
access to the computer and does not bypass Windows security or approval prompts.

## What has been completed

### Local AI foundation

- Connected Cypher to the local Ollama runtime and Hermes orchestration gateway.
- Added Fast, Deep and Vision model roles with deterministic routing.
- Added streaming responses, real cancellation, bounded context and local runtime status.
- Added a one-generation runtime benchmark without automatic retries, downloads or model switching.

### Resident Windows experience

- Added a compiled Windows host that starts with the user session.
- Added the global **Ctrl+Alt+Space** shortcut.
- Replaced the early floating interface with the Monochrome Signal command workspace.
- Added scalable custom title-bar controls, pin/maximize/close controls and responsive layout.
- Added metadata-only task recovery, safe failure receipts and cooperative upgrades.

### Permissions and file safety

- Added explicit folder grants instead of whole-computer file access.
- Added bounded folder listing, filename search and small text-file viewing.
- Added exact file-operation plans, one-time native approval, verification and protected Undo.
- Added cooperative Stop with rollback and a recovery-required state when safe reversal is impossible.
- Kept file content out of Hermes, research providers and persistent chat history.

### Windows application controls

- Added deterministic observation of visible windows and registered applications.
- Added approval-gated launch, focus, minimize, restore and supported text-entry actions.
- Added approval-gated delivery of one validated public HTTPS destination to one registered app.
- Added bounded multi-step workflows with revalidation before each action.
- Added exact packaged-app identity handling and ambiguity rejection.
- Kept passwords, clipboard automation, arbitrary shell execution and unrestricted UI automation unavailable.

### Research capabilities

- Added model-free `Web: links` / `Web: map` for at most six visible safe destinations.
- Kept link inspection separate from the existing approval-gated browser open action.
- Added grounded `Web: ask URL : QUESTION` with one installed local-model call and exact evidence.
- Added model-free `Web: read` and `Web: preview` for one explicit public HTTPS page.
- Added exact bounded page excerpts with no browser-state, model, file, or action access.
- Added bounded public-page research with checked sources and exact evidence passages.
- Added question-only discovery through official Wikipedia APIs.
- Added academic discovery through OpenAlex with a tightly limited Crossref fallback.
- Added local evidence ranking, citation checks and relationship-evidence screening.
- Kept research read-only, without logins, cookies, action tools or hidden retry loops.

### Local document workspace

- Added extractive `Docs: ask` and `Docs: summarize` commands.
- Added grounded `Docs: answer` with exact source passages and line citations.
- Added grounded comparison of **two to four** explicitly selected documents.
- Added model-free `Docs: search ROOT : query` for bounded content search in one approved folder.
- Raised explicit Docs routes to supported UTF-8 text files up to **1 MiB**.
- Kept the model evidence budget fixed at 4,096 passage-text bytes.
- Required a non-empty comparison to cite evidence from every supplied source.
- Added paths, line numbers, byte counts and SHA-256 snapshot digests to document evidence.
- Added the **DOC SEARCH**, **DOC ANSWER** and **DOC COMPARE** interface controls.
- Added explicit PDF ask, answer, summarize and mixed text/PDF comparison.
- Added a separately pinned PDF parser child that receives bytes without paths, model or actions.
- Added 8 MiB / 100-page PDF limits and exact page/line evidence.
- Added a separately pinned standard-library Office parser for DOCX, PPTX and XLSX bytes.
- Added strict ZIP/XML limits and exact paragraph, slide, sheet and row evidence locations.
- Kept macros, formulas, external relationships, embedded objects and legacy Office formats inactive.

## Current interface

The Ctrl+Alt+Space workspace now provides:

1. Ask Page
2. Research Papers
3. File Tasks
4. Document Search
5. Document Answer
6. Document Compare
7. New Chat and Copy Output

The interface uses an opaque black-and-white editorial/cyber-industrial theme with technical rails,
original signal artwork, compact status indicators and no decorative control that pretends to offer
an unavailable capability.

## Current validation state

- The 10.2.0 focused document suite has **52 passing tests**.
- The combined document/native-host gate has **108 passing tests**.
- DOCX, PPTX and XLSX package fixtures, format matching, resource limits, integrity and Stop pass.
- The complete suite runs **555 tests**: **554 pass** and one existing direct-run Windows platform
  check skips; its required native equivalent passes during installation.
- Native compilation, compiled host self-test, offline fixtures and WPF render pass.
- The transactional installer passed before switching the resident host.
- The live host is **READY** on `0.7.0-core-preview10.2.0`.
- Installed document, PDF, Office and file-worker hashes exactly match the release package.

## Current privacy and security boundary

- Cypher runs as the signed-in standard Windows user.
- Local model and Hermes connections are loopback-only.
- Consequential Windows and file actions require fresh human approval.
- Folder grants are explicit and removable.
- Document search is model-free and creates no persistent index.
- Document paths and filenames are not supplied to the local model.
- Prompt and response content is not placed in operational logs.
- There is no unrestricted command shell, arbitrary code tool or ambient computer access.

## Important current limitations

- PDF parsing is text extraction only; OCR, forms, attachments and PDF editing are unavailable.
- PDFs are limited to 8 MiB / 100 pages; text files remain limited to 1 MiB.
- Legacy DOC/PPT/XLS, macro-enabled Office packages, charts, images, comments and tracked-change
  semantics are not interpreted. Spreadsheet formulas are not evaluated.
- There is no persistent full-library document index or embedding database.
- Voice input and microphone control are not yet implemented.
- Vision/image understanding is not yet connected to the native workflow.
- Broader app-specific automation still needs separately reviewed capabilities.
- Generated document answers use conservative validation, but citations do not prove that every
  interpretation is semantically correct.

## Recommended next milestones

1. Add optional local OCR behind a distinct, bounded capability.
2. Add native image attachment and bounded local vision analysis.
3. Add user-reviewed durable tasks, reminders and scheduling.
4. Add opt-in memory with visible review, edit and deletion controls.
5. Expand app-specific workflows only through explicit permissions and deterministic verification.
6. Complete accessibility, usability and performance testing on the target PC.

## Current release package

The sealed release is stored in Desktop **cypher dev/Cypher-10.2.0**.
Use `INSTALL_CYPHER_OFFICE_DOCUMENTS.cmd` for a clean reinstall and `OFFICE_DOCUMENTS_SETUP.md` for
the focused usage guide. The complete 10.1.1 package remains the rollback baseline.
