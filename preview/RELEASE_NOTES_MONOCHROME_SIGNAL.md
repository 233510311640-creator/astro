# Cypher 9.7.1 — Monochrome Signal (retained by 9.8.0)

Core Preview 9.7.1; Python distribution 0.9.7a2. 17 September 2026.

## 9.7.1 refinement

- replaces the text and font-glyph title-bar controls with scalable pin, expand and close line icons;
- adds the original `cypher-signal-core.png` machine-intelligence artwork to the welcome surface;
- pins and verifies the artwork by SHA-256 before loading or installing it;
- keeps the earlier vector signal lattice as a safe fallback if the packaged image is missing or invalid;
- preserves every command, approval, recovery and keyboard behavior from 9.7.0.

The artwork was generated specifically for Cypher from the uploaded image's monochrome editorial mood.
It does not copy the reference's words, garment, character or layout.

## Purpose

This release redesigns the native Ctrl+Alt+Space workspace around the requested monochrome,
editorial sci-fi direction. It translates the reference's atmosphere rather than reproducing its
artwork, wording or exact composition.

## Visual system

- opaque near-black workspace with off-white text and square, hairline frames;
- Bahnschrift Condensed display typography, Segoe UI body text and Cascadia Mono telemetry;
- subtle local grid texture and an original abstract signal-lattice illustration;
- asymmetric mode, command and system regions with real numbered actions;
- a 1120×720 default window and retained 760×560 minimum;
- monochrome idle surfaces with cyan, green, amber and red reserved for semantic state;
- an amber left-edge approval card and persistent Stop/recovery access;
- visible keyboard-focus borders and descriptive automation names for important state controls.

The left rail contains Auto, Fast and Deep routing. The center remains the only response, evidence,
approval and command surface. The right rail exposes model route, local/private state, system status,
file-task status, new chat and copy output. Decorative reference-image labels are not used.

## Preserved behavior

The document, file, research, runtime and Windows workflows were unchanged. The release did not add
network providers, model calls, action authority, memory, microphone access, retries, downloads,
countdowns or paid APIs. Existing approvals, Stop, recovery, pin, expand, Escape-to-hide, Enter-to-send
and Shift+Enter behavior are retained.

The prior UI geometry key was intentionally replaced with `9.7.1`, allowing the new default aspect to
appear once instead of inheriting old 9.2.9 dimensions. Later moves and resizes are saved normally.

## Verification

The native WPF tree is parsed and exercised at minimum, default and common laptop dimensions. Tests
assert unique control names, control binding compatibility, visible mode/system/command regions,
reachable approval and Stop controls, an opaque window, disabled vision mode and read-only response.
The full inherited safety suite and all owned-worker offline fixtures must pass before installation.

The release candidate completed 525 automated tests (524 passed and 1 intentionally skipped), the
native host self-test, and a real WPF render check. The installer also resolves and verifies a
current-user Python 3.12 installation when the Windows Python launcher cannot enumerate it.

9.8.0 retains this visual system while adding grounded document answers. Keep the complete 9.7.1
package as reinstall rollback.
