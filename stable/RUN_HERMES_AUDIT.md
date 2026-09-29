# Run the Hermes/Ollama read-only audit

This audit does not install, configure, connect, update, delete, move, or modify anything. It does not read Hermes configuration contents, conversations, memory, browser data, credentials, or personal files. It makes one HTTP request to the local Ollama loopback endpoint and no internet request.

Version 0.3 prints a `[CHECK]` line before each stage. External Hermes and Ollama commands have a hard time limit, so a slow or unresponsive command is reported as a warning and the audit continues.

## Windows instructions

1. Extract this ZIP to a new folder such as `Desktop\Hermes audit`.
2. Open that folder.
3. Right-click an empty area and choose **Open in Terminal**.
4. Confirm the title does not say `Administrator`.
5. Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\audit_hermes_windows.ps1
```

6. Send the complete terminal output or screenshots for review.

If an older audit is sitting on a blank line, press `Ctrl+C`, close that folder, and use this version instead.

Do not connect accounts, paste API keys, install plugins, enable background tasks, or change Ollama networking during this phase.
