# Cypher 10.6.0 — Bounded Public Link Follow

Cypher can follow one numbered link from a freshly rebuilt public-page map and display up to four
exact excerpts from the destination. `Web: links URL` now displays a `Read command` beside each
eligible link; `Web: follow URL : NUMBER` performs the read. A Follow Link starter is available
in the command center's system rail. The command does not use a local model or browser profile.

The destination must remain on the mapped page's final host, including after redirects. A
disappeared number returns a clear partial result and makes no destination request. Both pages
use the existing public-address, DNS, robots, content-type, byte, request-count and time limits.

This is isolated read-only navigation, not browser clicking or form filling. Browser opening
still uses a separate exact Open command and one-time human approval. The 10.5.0 release remains
the rollback copy.
