# Security — bounded public form inspection

Only one explicitly supplied canonical public HTTPS page is fetched. The isolated reader
continues to enforce public-address, DNS, robots, redirect, content-type, byte, request
and time limits. The parser accepts HTML only and returns at most five GET/POST forms whose
canonical action stays on the final page host, with at most eight named non-sensitive
controls per form. Hidden, disabled, read-only, password, file and unnamed controls are
not listed. Values, options, hidden tokens and current browser state are never displayed.

Form metadata is untrusted page content. It cannot become a command, permission, approval
or model instruction. No request is made to a form action, and no form field is filled.
No browser profile, cookies, login, scripts, download, local model, file write, Windows
action, provider fallback or automatic retry is connected.

Static HTML inspection cannot prove computed browser visibility or whether scripts later
alter a form. GET endpoints can have server-side effects if requested by other software;
this route never requests them. Future submission requires a separate capability design.
