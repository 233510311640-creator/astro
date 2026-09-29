# Validation — Bounded Browser Search

Release: **Cypher 10.2.2** / **Core Preview 10.2.2**

Acceptance checks:

- direct and open-then-search language forms parse deterministically before model routing;
- public domains still use direct HTTPS opening;
- normalized search queries are limited to 300 characters and reject control/bidirectional-control characters;
- only a fixed DuckDuckGo HTTPS destination is generated;
- approval displays the query and external disclosure target;
- query, provider, URL, browser executable, hashes, and expiry are fingerprinted;
- validation rebuilds the URL from the approved query and compares it exactly;
- direct launch uses one argument with shell execution disabled;
- no page/result reading, clicking, screenshots, clipboard, raw keyboard input, cookies, login state, or shell fallback is added.
