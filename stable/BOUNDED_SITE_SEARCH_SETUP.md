# Bounded public site search

Install Cypher 10.8.0 with `INSTALL_CYPHER_BOUNDED_SITE_SEARCH.cmd`, press Ctrl+Alt+Space,
then enter `Web: search https://docs.python.org/3/ : asyncio`. The **Site Search** rail
button fills the command template but never sends it by itself.

Cypher fetches only the explicit public page first. It accepts one unique same-host GET
search action with one named `q`, `query`, `search`, `s`, `term` or `keywords` text/search
field, no hidden or sensitive controls, and no preexisting action query. Identical search
boxes count as one action. The typed query is capped at 200 characters/400 UTF-8 bytes.
Only after these checks does Cypher attempt one HTTPS GET and preview up to four exact
excerpts from the fetched page. Its final host stays pinned to the source page's host.

The query and this PC's public IP may reach the site. No POST, login, cookies, browser
profile, scripts, local model, file or Windows action is connected. Robots rules and the
existing public-address, DNS, redirect, content-type, byte and time limits apply. Some
search pages populate matches with JavaScript; this reader does not execute it, so the
page preview may contain only static text rather than actual result entries.
