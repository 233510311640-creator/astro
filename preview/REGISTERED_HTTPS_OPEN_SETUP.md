# Cypher 10.1.1 - Registered HTTPS Open

## Purpose

This release fixes natural requests such as:

```text
Open Brave then visit chess.com
Open Brave then search chess.com
Open Brave and navigate to https://www.chess.com/play
```

The request is parsed locally before general chat. `chess.com` becomes `https://chess.com/`.
The approval card shows the exact registered application and normalized destination.

## Register the application once

Cypher will not discover or grant access to applications automatically. If Brave is not already in
the human-managed registry, run this from the extracted release folder:

```text
MANAGE_CYPHER_WINDOWS_APPS add brave "Brave" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
```

Then check it with:

```text
MANAGE_CYPHER_WINDOWS_APPS list
```

Registration permits Cypher to propose actions for that exact executable. It does not execute an
action and does not enable text entry. Each HTTPS open still needs a fresh native approval.

## Install

Keep the complete 10.1.0 package for rollback. Run **INSTALL_CYPHER_REGISTERED_HTTPS_OPEN.cmd** and
confirm **CORE PREVIEW 10.1.1 / MONOCHROME SIGNAL** after pressing **Ctrl+Alt+Space**.

## Boundaries

- exactly one registered app and one destination;
- HTTPS only, with one DNS hostname and default HTTPS port;
- no credentials, whitespace, IP literals, local/reserved names or multiple destinations;
- one 60-second approval bound to app identity, executable hash and destination hash;
- one argument passed directly to the registered executable with no shell;
- no address-bar read, page inspection, login, clicking, typing, scraping or success claim about page load.

This feature delivers an exact URL to an approved application. It is not a general search engine or
interactive browser agent.
