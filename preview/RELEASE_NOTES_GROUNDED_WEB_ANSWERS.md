# Release notes — Cypher 10.4.0 Grounded Public Page Answers

- Adds `Web: ask PUBLIC-HTTPS-URL : QUESTION` before general chat routing.
- Accepts exactly one explicit public HTTPS page and one bounded question.
- Reuses the isolated reader's DNS, public-IP, robots, redirect, content-type, byte, and time limits.
- Supplies only bounded reader-assigned passages to at most one verified installed local-model call.
- Requires every displayed finding to select valid passage IDs and pass exact-source and conservative
  claim-scope checks.
- Shows exact supporting page text below the locally drafted findings.
- Performs no search, provider fallback, automatic retry, browser-session access, script execution,
  file operation, Windows action, or shell command.
- Treats the question and page as data; page content cannot grant action authority or change rules.
- Adds an **ASK PAGE** workspace card and a distinct **LOCAL · GROUNDED PAGE ANSWER** state.
- Retains `Web: read` and `Web: preview` for model-free exact page excerpts.

