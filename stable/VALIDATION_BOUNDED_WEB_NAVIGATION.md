# Validation — Cypher 10.5.0 Bounded Public Page Navigation

Validated 25–26 September 2026.

- Full regression suite: 566 tests, 565 passed, one existing platform skip.
- Native C# compilation and compiled self-test passed.
- Owned research, file, runtime and document worker self-tests passed.
- Workspace render passed with **MAP LINKS** and **ASK PAGE** cards.
- Transactional installer passed all pre-replacement checks and upgraded the resident host.
- Installed heartbeat reports READY on `0.7.0-core-preview10.5.0`.
- Installed research worker SHA-256 matches the hardened source:
  `7b1d05b24006ab8379d13c657c06ee3c6b3fb14080e175ee3d5a449957819a0f`.
- A live read-only request to `https://en.wikipedia.org/wiki/Example.com` completed with six
  same-host links and exact separately approvable Open commands. No link was opened.

Covered gates:

- parser accepts one explicit public HTTPS URL and rejects missing, multiple, local, IP-literal and
  non-HTTPS destinations;
- visible relative and same-site absolute links are canonicalized and deduplicated; off-site links are excluded;
- hidden, form, script, signed/credential-like, fragment and common download targets are excluded;
- at most six links are returned and no linked destination is fetched;
- link mapping makes no local-model call and no Windows action;
- the native transcript accepts the new route and keeps the six-finding output bound;
- the command center exposes **MAP LINKS**, preserves **ASK PAGE**, and fills the composer only;
- opening remains a separate exact browser command using the existing one-time approval;
- native compile, compiled self-test, owned-worker boundary test, workspace render and transactional
  installer gates pass before host replacement;
- the complete Python regression suite passes before release sealing.
