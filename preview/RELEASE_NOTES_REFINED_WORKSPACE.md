# Core Preview 9.2.10 — Refined Workspace

Package **v0.9.2.10** · Python package **0.9.2a11** · 8 September 2026

## Why this update

The user ran the 9.2.9 installer and asked for a more considered visual design, specifically citing
Dribbble, typography and color combinations. The prior dark layout removed clutter but still opened
with a long technical paragraph and gave most elements similar visual emphasis.

## Native interface changes

- Graphite surfaces with a restrained violet accent, soft panel contrast and rounded controls.
- Segoe UI Variable Text/Display family preferences with Segoe UI fallback. A 34-pixel welcome
  heading, 19-pixel brand, 18-pixel section heading and 15-pixel response text establish hierarchy.
  Font selection uses installed Windows fonts; nothing is downloaded or installed.
- A centered welcome view replaces the initial technical paragraph. Three usable cards fill a
  general-reference research, academic research or planning prefix. They never send a request.
- A violet composer with a visible empty-input hint, styled model selectors and Send control.
- A bounded 900-pixel content column and an inset response surface improve spacing. The original
  response remains selectable and scrollable; Copy retains its existing behavior and content.
- Research-route, provider and model guidance remains accessible under Session details. The current
  research report retains all of its original disclosures, diagnostics and source information.
- New chat clears the in-memory context and returns to the welcome view. Existing task guards remain.

The brand mark and line icons are original vector paths. No Dribbble screenshots, logos, templates,
paid design assets, browser runtime or external font dependencies are bundled. This changes the
compiled WPF UI, not just the included design references.

The 9.2.9 window size, geometry preference version, pin state, resize, expand, hotkey and animation
are retained. Existing action approval remains outside expandable details; review text scrolls while
Deny and Approve once remain visible. The review-text viewport is 80 pixels high so small windows
can retain the composer and action controls. Stop and recovery keep their existing lifecycle rules.

## Design references

Read on 8 September 2026:

- [Shahzaib Jugwal — AI Chat Dashboard, Dark Mode UI](https://dribbble.com/shots/26609268-Case-Study-AI-Chat-Dashboard-Dark-Mode-UI):
  contrast hierarchy around the composer, soft depth and rounded action controls informed this direction.
- [Arounda — UI/UX for AI Tools & Productivity Platforms](https://dribbble.com/shots/26962210-UI-UX-for-AI-Tools-Productivity-Platforms):
  reviewed the page and its large reference image for panel layering and separation of conversation
  from controls. Cypher does not adopt the reference's paid-plan/sidebar features or image-generation UI.
- [Barly Design / Uxerflow — Orbita AI](https://dribbble.com/shots/25828593-Orbita-AI-Chat-Assistant):
  reviewed its stated typography hierarchy and onboarding goals. The new Cypher layout is an original
  interpretation; no source asset is copied into the product.
- [Microsoft — Typography in Windows](https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/typography)
  and [WPF FontFamily fallback](https://learn.microsoft.com/en-us/dotnet/api/system.windows.media.fontfamily):
  informed the installed-font preferences and distinction between heading, body and supporting text.

The preview images use a substitute font and manually rendered layout. They are labelled design
references, not screenshots of WPF running. Exact font rendering and DPI behavior require Windows.
Older 9.2.9 preview files and release notes are historical; current images use `cypher-refined-*` names.

## Behavior and verification

The complete suite discovers 415 tests: **414 pass, one Windows-only compiler check is skipped**
on Linux. The 189-test research suite passes with EncodingWarning treated as an error. The new
starter guard verifies that clicks only edit enabled input and cannot dispatch network/model work.

The installer's existing pre-replacement native WorkspaceSelfTest now also checks the three starter
prefixes, disabled-input behavior and switching between welcome and response. The existing layout
checks cover normal/minimum sizes, long content and action approval. This native test has not been
executed in the Linux build environment; an unsuccessful native check stops replacement of the
running version. Source/XAML checks cannot prove Windows appearance or interaction.

Research worker bytes and their integrity pin remain exactly as delivered in 9.2.8. The query,
eight-candidate/two-source limits, preflight, zero-or-one model generation, exact-503 Crossref fallback,
runtime startup, broker permissions and workflow engine remain. No provider, query retry, action
authority or research-content persistence is added. The source-discovery comparison remains an open
backend gate; see [the evaluation specification](docs/ACADEMIC_DISCOVERY_EVALUATION.md).

## Install and observe

Keep 9.2.9 for reinstall rollback. Extract the full ZIP into a fresh folder and double-click
**INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally as the standard user. Press **Ctrl+Alt+Space** and
confirm **CORE PREVIEW 9.2.10** in the footer. A prompt-card click should fill the composer only;
edit it before Send. New chat returns to the welcome view when no request is active.

A screenshot of the interface would establish the actual Windows result. No repeat of the previous
academic question is required merely to check colors, fonts or layout. The legacy manager's rollback
target remains 0.6.3; reinstall the retained 9.2.9 package to return specifically to that release.
