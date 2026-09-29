# Bounded public link follow

Cypher 10.6.0 adds a read-only two-page route. Install with
`INSTALL_CYPHER_BOUNDED_LINK_FOLLOW.cmd`, then press Ctrl+Alt+Space.

1. Enter `Web: links https://example.org/` and Send.
2. Choose a numbered result and submit its displayed `Read command`, for example
   `Web: follow https://example.org/ : 1`.
3. Cypher re-reads the first page, selects that number from the current same-host map, and
   displays up to four exact excerpts from the destination. If the number disappeared, remap.

This route makes public HTTPS requests from an isolated reader. It observes robots rules and
public-address, DNS, redirect, content-type, byte and time limits. A linked page that redirects
off the source host is blocked before fetching the redirected destination. No login, browser
profile, script, form submission, click, download, local model, file operation or Windows action
is available. Source text and links never gain instruction authority. The report is memory-only.

To open a link in your browser instead, submit its separate `Open command` and review Cypher's
existing one-time approval.
