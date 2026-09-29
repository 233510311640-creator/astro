# Release notes — Cypher 10.3.0 Isolated Public Page Read

- Adds `Web: read PUBLIC-HTTPS-URL` and the equivalent `Web: preview` command before model routing.
- Accepts exactly one explicit public HTTPS URL; no search or URL discovery is performed.
- Reuses the isolated reader's DNS, public-IP, robots, redirect, content-type, byte, and time limits.
- Returns at most four exact excerpts from the checked page and identifies the verified final URL.
- Makes no local-model call and does not add page text to chat history.
- Gives the reader no browser profile, cookies, saved passwords, login state, scripts, file tools,
  Windows actions, shell, or general tool access.
- Treats all page content as untrusted data that cannot authorize an action or change Cypher's rules.
- Adds a **READ PAGE** workspace card and a distinct **ISOLATED · PUBLIC PAGE READ** state.
- Leaves browser opening, bounded search, research synthesis, documents, and Windows actions unchanged.

