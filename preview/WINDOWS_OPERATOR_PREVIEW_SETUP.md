# Cypher v0.8.2 Windows Operator Preview 2

This build is the first Cypher milestone that controls ordinary Windows application state instead
of only files. It adds six real Windows tools while preserving the existing file operator.

## What it can do

- list visible top-level application windows;
- report the current foreground window;
- list apps registered for Cypher launch;
- launch Notepad, Calculator, Paint, or File Explorer when present;
- focus an existing visible window and report whether Windows actually accepted the request;
- continue using the existing sandbox, inventory, organization, and real-folder tools.

The build does not yet click controls, type text, capture screenshots, close programs, or run an
arbitrary command. Those functions need the next application-action layer rather than a raw shell.

## Install or upgrade

1. Finish or stop any task currently running in Cypher.
2. Extract the ZIP into a new folder named `cypher-v0.8.2-windows-operator-preview2`.
3. Double-click `INSTALL_CYPHER_WINDOWS_OPERATOR_PREVIEW.cmd`.
4. After it passes, open a normal PowerShell window in this new folder.
5. Run `hermes mcp remove hermes-sandbox` and answer `y`.
6. Open `REGISTER_COMMAND.txt`, copy its one command into PowerShell, and run it.
7. Double-click `CONFIGURE_CYPHER_HERMES_TOOLS.cmd`. It should report a healthy connection.
8. Press `Ctrl+Alt+Space` to reopen Cypher.

You do not need to run the brain evaluator again. Existing folder permissions, operator plans,
models, Hermes data, and Ollama model files are preserved.

## Acceptance prompts

Start with read-only observation:

> Use the exact Windows tools. List my registered apps and visible top-level windows. Do not launch
> or focus anything.

Then test an ordinary reversible action:

> Use the exact Windows tools to launch the registered Notepad app. Report the process ID and whether
> a Notepad window was actually observed. Do not type anything.

Finally test focus:

> List visible windows, identify the Notepad window ID, then ask Windows to focus it. Report whether
> focus was actually observed.

## Add another application later

From PowerShell in the extracted folder:

```powershell
.\scripts\manage_windows_apps_windows.ps1 add vscode "Visual Studio Code" "C:\Path\Code.exe"
```

Cypher never supplies command-line arguments to a registered app. Restart Hermes or run
`/reload-mcp` after changing the app list.

## Rollback

The previous extracted release remains untouched. Re-register `hermes-sandbox` with that release's
`REGISTER_COMMAND.txt` to return to its broker. The resident Core retains its existing cooperative
rollback manager.
