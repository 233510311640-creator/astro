# Isolated Public Page Read setup

Release: **Cypher 10.3.0** / **Core Preview 10.3.0**

## Install

Keep Cypher 10.2.2 as the rollback copy. Extract the complete 10.3.0 release into a new folder and
run `INSTALL_CYPHER_ISOLATED_PAGE_READ.cmd` normally. No administrator permission is required.

After installation, press **Ctrl+Alt+Space** and confirm the footer says:

```text
CORE PREVIEW 10.3.0 / MONOCHROME SIGNAL
```

## Use

Type either command with one complete public HTTPS URL:

```text
Web: read https://example.org/
Web: preview https://example.org/
```

The **READ PAGE** card fills the first command prefix. Add the URL and press **Send**. Cypher checks
the destination through its isolated reader and shows at most four exact excerpts. No approval is
needed because this route cannot run an app or change a file.

## Boundary

This is a public-page text preview, not control of an open browser tab. It cannot use a signed-in
session, cookies, saved passwords, JavaScript-only content, forms, clicks, downloads, screenshots,
or local/private addresses. It does not summarize with a model. Use a separate `Research:` command
when you explicitly want bounded local-model synthesis from public sources.

