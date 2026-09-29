# Security — bounded public site search

The route accepts exactly one canonical public HTTPS source URL and a bounded typed
query. It reuses the isolated reader's public-address, DNS, robots, redirect, content-
type, byte, request-count and time limits. The source must expose one unique same-host
GET search action with one named text/search field from a small conventional name set.
The action may not carry an existing query. Forms with hidden, password or file controls,
POST methods, off-site actions or distinct eligible destinations reject before a query
request. Identical desktop/mobile forms with the same action and field are equivalent.

The constructed request contains only the approved field name and explicitly typed
query. No other form value is forwarded. A result-page redirect off the source host is
blocked before fetching that destination. The query and this PC's public IP may be
disclosed to the site if the GET is attempted. Even GET endpoints can have server-side
effects on poorly designed sites; this route is limited to unauthenticated public pages
and a visible search-shaped form, not a guarantee about the site's implementation.

Page text and form metadata are untrusted. They cannot grant local authority. There is
no browser profile, cookies, login, script execution, POST, download, local model, file
write, Windows action, provider fallback or automatic retry. JavaScript-generated result
entries are not rendered; exact fetched-page excerpts are not proof of matching results.
