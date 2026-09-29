# Cypher 10.2.1 — Auto-Discovered Browser Open

Cypher can open a public HTTPS destination in Brave, Microsoft Edge, Google Chrome, or Mozilla Firefox without first adding that browser to Cypher's application registry.

## Install

Run `INSTALL_CYPHER_AUTO_BROWSER_OPEN.cmd` normally. After installation, press **Ctrl+Alt+Space** and confirm **CORE PREVIEW 10.2.1 / MONOCHROME SIGNAL**.

## Examples

- `Open Brave then search chess.com`
- `Open Edge then visit openai.com`
- `Open Chrome then open https://example.com/`
- `Open Firefox then visit wikipedia.org`

Cypher discovers only those four known browsers and only at fixed standard Windows installation paths. It displays the exact executable, file hash, and normalized HTTPS destination for one-time approval before launching it directly. It does not use a shell, search `PATH`, inspect the page, read the address bar, or interact with website content.

Other applications still require explicit registration. This milestone opens a reviewed destination; it does not yet provide autonomous page navigation or website interaction.
