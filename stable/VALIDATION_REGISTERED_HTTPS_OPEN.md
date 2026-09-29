# Cypher 10.1.1 validation - Registered HTTPS Open

## Completed

- the exact screenshot phrase parses as `Brave` plus `https://chess.com/`;
- the route precedes natural text, generic launch and model dispatch;
- public HTTPS normalization and app/executable/URL fingerprinting are covered;
- HTTP, localhost, IP-literal, credentialed, whitespace and ambiguous destinations reject;
- an unregistered app produces a deterministic registration error instead of model refusal;
- approval UI shows the exact app and destination;
- execution uses one direct argument with `UseShellExecute=false` and no shell/raw-input fallback;
- focused Windows-host suite: 56 tests pass;
- complete suite: 550 tests run, 549 pass and one existing direct-run Windows platform check skips;
- compiled host self-test, offline fixtures and real WPF workspace render pass;
- transactional installation passes before replacing the resident host;
- live heartbeat reports `ready` on `0.7.0-core-preview10.1.1`;
- installed document, PDF-parser and file-worker hashes exactly match this release package.

## Installation result

Cypher 10.1.1 is installed and running. The render-only verification produced
`docs/cypher-registered-https-open-preview.png` without opening a browser or website.

No live website request is required for these gates. A later human acceptance check may register
Brave and approve one `Open Brave then visit chess.com` action; the result should report URL delivery,
not claim that Cypher inspected or verified the page.
