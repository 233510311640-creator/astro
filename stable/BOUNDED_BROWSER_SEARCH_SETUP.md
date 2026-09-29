# Cypher 10.2.2 — Bounded Browser Search

Run `INSTALL_CYPHER_BOUNDED_BROWSER_SEARCH.cmd` normally. Press **Ctrl+Alt+Space** and confirm **CORE PREVIEW 10.2.2 / MONOCHROME SIGNAL**.

## Commands

- `Search the web for local-first AI assistants in Brave`
- `Look up Sicilian Defence using Edge`
- `Open Chrome then search chess openings`
- `Open Firefox then search for Windows accessibility APIs`

Cypher normalizes a query of at most 300 characters and builds one fixed HTTPS request to DuckDuckGo. Before execution, the approval card shows the exact query, destination, browser executable, and integrity hashes. Approving discloses the displayed query to DuckDuckGo through the selected browser.

A domain-like value such as `Open Brave then search chess.com` remains a direct HTTPS open. Search queries containing control or bidirectional-control characters reject. Brave, Edge, Chrome, and Firefox can be discovered only from fixed standard Windows installation paths; arbitrary applications remain registered-only.

This release delivers a search URL. It does not read search results, inspect the address bar, click links, use a logged-in browser profile, or verify network/page success.
