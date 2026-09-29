# Core Preview 9.2.9 — Dark Workspace

Package **v0.9.2.9** · Python package **0.9.2a10** · 8 September 2026

## What changed

Cypher now uses an opaque near-black native window with a single conversation column. The large
decorative orb, placeholder navigation, model cards and fixed right sidebar are removed. Text is
larger and more legible; borders and accent colors are quieter. The existing full response remains
selectable, scrollable and available through Copy response.

- Default size: 1040 × 740 logical pixels; minimum: 760 × 560. Resize, drag, pin, expand and the
  Ctrl+Alt+Space hotkey remain. The first launch resets old oversized geometry and retains the pin
  preference. Later launches restore the new geometry, clamped fully into the primary work area.
- Auto, Fast and Deep sit above the input. The unavailable Vision control is hidden and remains
  disabled. There is no model change or download.
- Send and Stop stay beside the input. Stop retains its existing enabled/disabled lifecycle.
- The latest phase stays visible. Session details expands to show task evidence and capabilities;
  Retry task status remains outside that section.
- Existing action approval has a separate visible card. Its complete review text scrolls while
  Deny and Approve once stay below it. Session details yields space while the card is present.
- Custom buttons, mode controls and the details toggle show keyboard focus. Scrollbars use the
  dark palette. Enter sends, Shift+Enter inserts a line and Esc hides Cypher.

The changes are in the existing compiled WPF host. This is not a browser UI and adds no web runtime,
theme download, account, dependency or persistent conversation storage. Only layout preferences
continue to be written by the existing UI-state code.

## Research and runtime status

The user's 9.2.8 screenshot verifies the observed preflight path: both selected sources had zero
passing passages and synthesis was skipped. It does not establish cold-start behavior, latency,
VRAM use or better research coverage. The autonomy/performance question remains unanswered.

The **research worker remains byte-for-byte identical to 9.2.8**, including its component version
and user agent. Its SHA-256 remains
`0db1f5957603649a1dbc093b50f56bffd4254076ea668f0bb1460ff0e54d3419`.
Search queries, eight-candidate/two-source limits, exact-503 Crossref fallback, passage checks and
the zero-or-one synthesis path are retained. No inference is made from the UI preview's sample text.

The next discovery evaluation is recorded in [the comparison plan](docs/ACADEMIC_DISCOVERY_EVALUATION.md).
A documented proximity query is a candidate for investigation, not an implemented improvement.
This environment did not provide a usable live API comparison, so there is no new search-quality
claim and no request to reinstall solely to repeat the old research question.

## Verification and practical limits

The complete Python suite discovers 414 tests: 413 pass and one native Windows compiler test is
skipped on Linux. The 189-test research suite also passes with EncodingWarning treated as an error.
The release is checked from a fresh extraction with a complete SHA-256 manifest. Native XAML is
XML-parsed and every C# FindName binding is checked against the named control type. Approval,
Stop and recovery controls are checked to stay outside the collapsible details section.

The installer now runs a native **WorkspaceSelfTest** inside its existing pre-replacement self-test.
It builds and measures the actual WPF tree at 760 × 560, 1040 × 740 and 1365 × 768 with long content,
details open/closed and approval visible/hidden. It checks control bounds without showing a window,
loading user content or making requests. Failure prevents replacement of the running host.
This new native test has not executed in the Linux build environment. Real Windows rendering,
DPI scaling, keyboard navigation and resizing still require target-PC observation.

The images under `docs/` are explicitly labelled **design references**, rendered with a substitute
font. They help review spacing and color; they do not demonstrate native WPF execution. Their small
approval example is illustrative, and does not represent a pending or executed Windows action.

Implementation references: [WPF ScrollBar parts](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/controls/scrollbar)
and [WPF Expander](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/controls/expander).

## Install

Keep the 9.2.8 ZIP for reinstall rollback. Extract the entire new ZIP into a fresh folder, then
double-click **INSTALL_CYPHER_RESEARCH_PREVIEW.cmd** normally, as the standard user. Open Cypher
with Ctrl+Alt+Space and confirm **CORE PREVIEW 9.2.9**. The legacy manager's rollback target remains
0.6.3; reinstall the retained 9.2.8 package to return specifically to that release.

The useful live check for this release is the interface: open it, resize it and confirm the input
and Send/Stop remain visible. A screenshot can establish the actual appearance. No new research
repeat, model diagnostic, permission prompt or Stop test is required.
