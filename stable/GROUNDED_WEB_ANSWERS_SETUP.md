# Grounded Public Page Answers setup

Release: **Cypher 10.4.0** / **Core Preview 10.4.0**

## Install

Keep Cypher 10.3.0 as the rollback copy. Extract the complete 10.4.0 release into a new folder and
run `INSTALL_CYPHER_GROUNDED_WEB_ANSWERS.cmd` normally. No administrator permission is required.

After installation, press **Ctrl+Alt+Space** and confirm:

```text
CORE PREVIEW 10.4.0 / MONOCHROME SIGNAL
```

## Ask one page

```text
Web: ask https://example.org/ : What is this page intended for?
```

The spaces around the separator colon make the page URL and question unambiguous. The **ASK PAGE**
card fills the command shape; replace the URL placeholder and type the question after the final
colon. Cypher reads only that page, makes at most one installed local-model call, and shows exact
supporting passages for accepted findings.

For a model-free page preview, continue using:

```text
Web: read https://example.org/
```

## Boundary

This does not inspect an open browser tab or signed-in session. It cannot use cookies, saved
passwords, JavaScript-only content, forms, clicks, downloads, screenshots, local/private addresses,
files, or Windows actions. It does not search for another page or retry through another provider.
If the local draft cannot be verified against the bounded page passages, Cypher withholds it.

