# Security boundary — Isolated Public Page Read

`Web: read` is a narrow read-only network capability. It receives only one user-supplied public
HTTPS URL. It has no browser state, cookies, login credentials, local file paths, action approvals,
Windows-control handles, shell, or model tools.

Before and during the request, Cypher canonicalizes the URL, rejects non-public destinations,
checks DNS results, follows only bounded validated redirects, applies robots policy, accepts only
supported text content, and enforces response and time limits. The worker runs as an owned,
integrity-pinned child with memory, process-count, and Windows UI restrictions.

Returned page text remains untrusted. It is not interpreted as an instruction, is not fed to an
action planner, and cannot grant permission. The authoritative output is the exact bounded excerpt,
not an inferred claim about the rest of the page or a JavaScript-rendered browser view.

