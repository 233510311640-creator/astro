# Security Boundary — Resident Host v0.6.3

## Security claim

v0.6 provides a convenient resident interface without increasing Hermes' tool authority. It is an activation and transport layer over the already configured Hermes Agent, local Ollama model, and v0.5 capability broker.

The v0.6.3 interface is implemented with local WPF controls. It does not embed a browser or WebView, load remote interface resources, execute response markup, or add a network listener. Lightweight formatting creates text-only WPF document elements from the returned response.

The host starts automatically, but it does not autonomously invent or schedule work. A user must press `Ctrl+Alt+Space`, double-click the tray icon, or select **Open assistant** before a request begins.

## Process and network boundary

- The resident host, MCP broker, and Ollama run under the current Windows user. Hermes' gateway runtime uses its supported Windows login registration.
- Hermes may request one UAC approval while creating or updating its Scheduled Task. The resident host never self-elevates, and no Windows service is created by this package.
- Hermes' API binds to `127.0.0.1:8642` only.
- The resident script rejects a configured endpoint unless its scheme is `http` and its host is `127.0.0.1`, `localhost`, or `::1`.
- The installer does not configure CORS.
- Requests require a random 32-byte bearer key.
- Ollama is checked only at `127.0.0.1:11434`.

Loopback prevents direct access from other computers. It does not isolate mutually untrusted processes running as the same Windows user.

## Credential handling

Hermes requires its API key in `%LOCALAPPDATA%\hermes\.env`. The installer owns only the block between:

```text
# BEGIN LOCAL_ASSISTANT_HOST_V0_6
# END LOCAL_ASSISTANT_HOST_V0_6
```

It refuses to overwrite API settings outside this block. A pre-install backup of `.env` is made once when that file already exists.

The tray host stores a second copy at `%LOCALAPPDATA%\LocalAssistantHost\api_key.dpapi`, encrypted using Windows DPAPI for the current user. The key is never placed in a command-line argument, host event log, prompt, response, or notification.

Limit: a malicious process already running as the same user can generally read Hermes' plaintext `.env` or call DPAPI as that user. BitLocker protects data when the computer is powered off; it is not process isolation while signed in.

## Tool authority

The resident host calls Hermes' Responses API. It does not provide a second execution engine and does not:

- enable Hermes terminal, file, code-execution, browser, or computer-use built-ins;
- pass a `--yolo` or equivalent flag;
- run arbitrary commands supplied by the user or model;
- approve MCP plans;
- bypass broker fingerprints, expiry, root containment, overwrite prevention, or undo requirements; or
- claim a side effect succeeded merely because the model said so.

The existing `hermes-sandbox` MCP configuration remains the enforceable capability boundary.

## Local persistence

The resident-host directory contains:

| File | Contents |
| --- | --- |
| `host_config.json` | Assistant name, loopback endpoint, conversation identifier, feature flags |
| `api_key.dpapi` | DPAPI-protected API bearer key |
| `heartbeat.json` | PID, status, version, last heartbeat timestamp |
| `host-events.jsonl` | Event name, outcome, timestamp, duration |
| `host-events.previous.jsonl` | Previous bounded event log, if rotation occurred |

The host event log does not contain prompt text, response text, tool arguments, file paths from requests, API keys, or model reasoning.

Hermes separately stores local session and response history. Rotating to a new conversation does not delete the older Hermes record. Retention controls for Hermes history are a future privacy milestone.

## User controls

- **Pause activation** makes the hotkey and tray activation refuse new requests.
- **Exit until next sign-in** shuts down the tray host.
- The manager's `stop` action writes a cooperative stop request and waits for the exact host heartbeat to disappear; it does not use `taskkill` or kill an arbitrary PowerShell PID.
- Uninstall requires the exact text `REMOVE RESIDENT HOST`.
- Uninstall validates the exact `%LOCALAPPDATA%\LocalAssistantHost` path before recursive removal.

## Not present in v0.6

- microphone access
- wake-word monitoring
- speech transcription or synthesis
- camera or screen capture
- autonomous schedules
- native approval prompts
- LAN or internet listeners
- administrator tools or administrator authority exposed to the model

## Acceptance tests

Do not accept the milestone if any of these fail:

1. All packaged tests pass.
2. `hermes gateway status` reports a standard-user Windows login installation.
3. `http://127.0.0.1:8642/health` returns healthy after sign-in.
4. `Ctrl+Alt+Space` opens one command window without PowerShell appearing.
5. A harmless local request returns a response.
6. A second launch does not create a second tray host.
7. Pause blocks activation and resume restores it.
8. Existing broker safety status still reports no real-folder execution.
9. Host event logs contain no test prompt or response text.
10. Uninstall removes the host shortcut and managed API block without deleting Hermes, broker state, or personal files.
