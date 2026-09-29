# Validation — Isolated Public Page Read

Release: **Cypher 10.3.0** / **Core Preview 10.3.0**

Acceptance checks:

- `Web: read` and `Web: preview` route locally before general model handling;
- exactly one explicit public HTTPS URL is accepted;
- missing, multiple, HTTP, credentialed, private, loopback, local, and unsupported URLs reject;
- DNS and every resolved address are checked before a permitted request;
- redirects are bounded and every destination is checked again;
- robots policy, content type, response size, and time limits remain enforced;
- page extraction yields one to four exact, source-backed excerpts;
- the route performs no discovery, model call, browser-profile access, file operation, or Windows action;
- page content is displayed as untrusted data and cannot approve or initiate an action;
- native source self-test, worker fixtures, integrity pins, and transactional installation pass.

Verified on 21 September 2026: all **559** automated tests passed with one existing platform skip;
the compiled host self-test and owned-worker fixtures passed; the transactional installer completed;
the live heartbeat reported `ready` on `0.7.0-core-preview10.3.0`; and installed research, file, and
document worker hashes matched the release package. A live installed-worker read of
`https://example.org/` completed with one checked source and two exact excerpts, no model phase,
and no model-use wording in the final report.
