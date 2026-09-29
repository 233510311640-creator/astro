# Local Windows Assistant Resident Host v0.6.3

v0.6 turns the tested Hermes/Ollama foundation into a resident Windows assistant. It starts at sign-in, stays in the notification area, and opens with `Ctrl+Alt+Space`. Normal chat no longer needs a terminal.

v0.6.3 replaces the temporary Windows Forms prompt and response dialogs with a single dark WPF overlay. It provides one prompt bar, an in-window thinking state, lightweight response formatting, copy and new-chat controls, and `Esc` to dismiss. The interface is native Windows UI: no browser, WebView, or additional network listener is introduced.

The existing v0.5 broker and its sixteen tool boundaries are not replaced. This package adds an interface and lifecycle layer, not broader authority.

## What the one-time installer changes

The installer performs the following visible, reversible changes:

1. Runs all packaged tests.
2. Copies the resident runtime to `%LOCALAPPDATA%\LocalAssistantHost`.
3. Adds a marked block to `%LOCALAPPDATA%\hermes\.env` enabling Hermes' API on `127.0.0.1:8642` with a random 256-bit bearer key.
4. Stores the host's copy of that key with Windows DPAPI for the current user.
5. Installs Hermes' gateway once, or restarts it only when an existing gateway registration is detected. On this Hermes/Windows build, Windows may show one UAC prompt so Hermes can create or update its Scheduled Task. The resident host still runs as the signed-in user.
6. Creates `Local Assistant Host.lnk` in the current user's Startup folder.
7. Starts the tray host immediately.

The installer runs 76 current production and resident-host tests. It intentionally excludes the retired v0.1 natural-language organizer prototype suite, which is not part of the Hermes capability broker and uses a Windows-incompatible `%TEMP%` fixture.

The installer refuses to overwrite pre-existing `API_SERVER_*` settings that are outside its marked block. It does not enable CORS, bind Hermes to the LAN, enable built-in tools, change the MCP broker, or use a microphone. Any UAC prompt comes from Hermes' own Scheduled Task installer; the resident host does not self-elevate.

## Install once

1. Extract this ZIP into a new folder. Do not merge it into v0.5.
2. Open a normal, non-administrator PowerShell in the extracted folder.
3. Run:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\scripts\install_resident_host_windows.ps1 -AssistantName "Hermes"
   ```

You may replace `Hermes` with a short name containing letters, numbers, spaces, `_`, or `-`. The name can be changed by running the installer again.

Stop if the tests fail, Hermes reports a gateway failure, or the installer cannot verify `http://127.0.0.1:8642/health`.

During a first gateway installation, choose **start now**, **start automatically at Windows login**, and approve the single UAC prompt. The installer then waits for Hermes to finish. If a second `Install it now` or `Open the UAC prompt now` sequence appears, cancel that repeated sequence and use v0.6.3 instead of an older package.

## Use it

After installation:

- press `Ctrl+Alt+Space`; or
- double-click the assistant icon in the notification area.

Type a request and select **Send**, or press `Enter`. Use `Shift+Enter` for a new line and `Esc` to hide the overlay. Hermes and Ollama handle the request locally, and the final response appears inside the same Cypher window.

The tray menu provides:

- Open assistant
- Status
- Start new conversation
- Pause or resume activation
- Exit until next sign-in

The first harmless test should be:

```text
Reply exactly: RESIDENT READY
```

Then test that the broker remains the boundary:

```text
Use only the hermes-sandbox tools. Call organization_status and report whether execution, content reads, and real-file writes are available. Do not propose or change anything.
```

Expected: execution false, content reads false, and real-file writes false.

## Privacy behavior

- The tray host makes HTTP requests only to the loopback Hermes endpoint.
- The API has a bearer key and no browser CORS permission.
- The tray host log contains event names, outcomes, timestamps, and durations—not command or response text.
- Hermes still stores local conversation/session history in its own SQLite state. **Start new conversation** stops using the old context but does not delete the old history.
- The microphone is not opened or monitored in v0.6.
- No paid model API is used; the configured Ollama model remains the inference backend.

The plaintext key in Hermes' own `.env` is readable by processes already running as the same Windows user. DPAPI protects the tray host's separate copy against other Windows accounts, but this design cannot protect against malware already running under your account. See [`SECURITY_RESIDENT_HOST_V0.6.md`](SECURITY_RESIDENT_HOST_V0.6.md).

## Diagnostics and lifecycle

These commands are optional; normal use does not need them:

```powershell
& "$env:LOCALAPPDATA\LocalAssistantHost\manage_resident_host_windows.ps1" status
& "$env:LOCALAPPDATA\LocalAssistantHost\manage_resident_host_windows.ps1" stop
& "$env:LOCALAPPDATA\LocalAssistantHost\manage_resident_host_windows.ps1" start
```

`stop` is cooperative and does not kill an arbitrary PowerShell process. The host starts again at the next Windows sign-in.

## Remove the resident layer

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$env:LOCALAPPDATA\LocalAssistantHost\manage_resident_host_windows.ps1" uninstall
```

Read the summary and type `REMOVE RESIDENT HOST` exactly. This removes the tray host, Startup shortcut, local token, and managed Hermes API block. It leaves Hermes, Ollama, the broker, conversations, and personal files intact. The Hermes gateway registration is preserved in case other Hermes features use it.

## Current milestone limits

- Activation is a global keyboard shortcut, not a spoken wake word.
- There is no speech-to-text or text-to-speech yet.
- There is no native approval-center window yet; the v0.5 organizer remains dry-run-only.
- Internet research and unrestricted computer control remain disabled.
- Only one foreground request runs at a time.

The intended next milestone is push-to-talk with a visible recording state, local transcription, no raw-audio retention, and typed confirmation for impactful actions.
