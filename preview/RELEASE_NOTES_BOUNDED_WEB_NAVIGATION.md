# Release notes — Cypher 10.5.0 Bounded Public Page Navigation

- Adds `Web: links PUBLIC-HTTPS-URL` and the equivalent `Web: map` command.
- Maps at most six visible, deduplicated same-site HTTPS links from one explicit page.
- Adds a **MAP LINKS** starter card and the **ISOLATED · SAFE LINK MAP** state.
- Provides a ready-to-submit `Open Brave then visit …` command for every mapped destination.
- Reuses the existing DNS, public-address, robots, redirect, content-type, response-size and deadline limits.
- Keeps link inspection model-free and outside chat/action history.
- Keeps opening separate and behind the existing executable-bound, destination-bound one-time approval.
- Excludes off-site, hidden, form, script, fragment, credential-like, signed and common download targets.
- Adds no cookies, saved passwords, login state, JavaScript, form submission, click automation, download,
  arbitrary browser profile, shell access, background retry or lasting approval.
