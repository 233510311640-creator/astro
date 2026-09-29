# Validation — Grounded Public Page Answers

Release: **Cypher 10.4.0** / **Core Preview 10.4.0**

Acceptance checks:

- the exact `Web: ask URL : QUESTION` form routes before general model chat;
- exactly one explicit public HTTPS URL and one non-empty bounded question are accepted;
- missing, multiple, HTTP, credentialed, private, loopback, local, and unsupported URLs reject;
- the isolated reader retains DNS, public-address, robots, redirect, type, byte, and time bounds;
- no discovery, provider fallback, or automatic retry occurs;
- only bounded reader-assigned passages reach at most one verified installed local-model call;
- model output cannot provide its own quote text or unknown passage IDs;
- accepted findings pass exact-source and conservative claim-scope validation;
- exact supporting passages and the verified final public URL are displayed;
- page content cannot invoke a tool, approve an action, or enter action/chat history;
- native source tests, compiled self-test, owned-worker fixtures, integrity pins, transactional
  installation, live heartbeat, and a neutral live page-answer check pass.

Verified on 25 September 2026: all **562** automated tests passed with one existing platform skip;
the compiled host self-test and owned research/file/runtime/document worker fixtures passed; the
transactional installer completed; and the live heartbeat reported `ready` on
`0.7.0-core-preview10.4.0`. Installed research, file, and document worker hashes matched the source
release. A live `https://example.org/` request produced the expected READING and SUMMARIZING phases,
one grounded finding, one exact supporting excerpt, and a completed `OK` result.
