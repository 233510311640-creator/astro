# Cypher 9.7.1 validation — Monochrome Signal (historical)

## Automated gate

The installer must complete all Python safety suites, native compilation, the WPF layout self-test,
and the existing research, file, runtime and document offline fixtures before it replaces the live
host. Any failure leaves the installed host unchanged.

Completed on 17 September 2026:

- 525 automated tests run: 524 passed, 1 intentionally skipped;
- the native Windows host compiled successfully and its self-test returned success;
- the real WPF tree rendered to `docs/cypher-monochrome-signal-preview.png` and was visually checked;
- the Python 3.12 resolver was exercised with the interpreter installed for the current Windows user.

The 9.7.1 visual refinement additionally checked that the SHA-256-pinned hero artwork loads into the
real WPF tree and that the three title-bar controls use scalable vector paths rather than text glyphs.

## One live visual handoff

1. Keep the 9.6.0 folder as rollback.
2. Run `INSTALL_CYPHER_MONOCHROME_SIGNAL.cmd` from the complete 9.7.1 folder.
3. Press **Ctrl+Alt+Space** and confirm the footer says **CORE PREVIEW 9.7.1 / MONOCHROME SIGNAL**.
4. Confirm the mode rail, central command workspace and system rail are fully visible.
5. Use Tab and Shift+Tab. Focus must remain visible on modes, shortcuts, the input, Send and Stop.
6. Resize to the supported minimum. No rail, composer, approval button or Stop control may leave the
   window; welcome content may scroll.
7. Enter a harmless local prompt such as `What can you do?` and confirm the welcome view becomes the
   readable response surface. Press Escape to hide, then Ctrl+Alt+Space to restore.

No file change or Windows-control approval is required for this visual gate. If an approval state is
encountered naturally, verify that its amber panel exposes both **DENY** and **APPROVE ONCE** without
approving the action solely for appearance testing.

This is the retained 9.7.1 visual record. The current 9.8.0 document gate is documented separately
in `VALIDATION_GROUNDED_DOCUMENTS.md` and `DOCUMENT_ANSWERS_SETUP.md`.
