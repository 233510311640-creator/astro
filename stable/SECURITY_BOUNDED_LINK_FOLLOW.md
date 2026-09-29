# Security — bounded link follow

The new route accepts exactly one canonical public HTTPS source URL and a number from 1 to 6.
It fetches that source anew, extracts only visible same-host eligible links, selects the current
number, then reads one destination with the source host pinned through redirects. It never uses
the user's browser session, cookies, saved passwords, login, scripts, forms, downloads, local
files, Windows actions, a model call or persistent task history.

Source and destination HTML are untrusted data. Link labels are displayed as provenance, not
instructions. External pages cannot select a different route or authorize a local action.
The `Web: links` result includes separate Read and Open commands; neither is executed by the map.
Open remains an existing destination-bound, executable-bound one-time approval.

Known limits: numbering can change between the map and follow command; Cypher rebuilds the map
and reports a missing number. Public HTTPS GET requests may be logged by the remote site. This
route does not support authenticated pages, cross-site links, forms, JavaScript, browser DOM,
downloads or multi-step navigation.
