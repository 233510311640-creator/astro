param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("list", "show", "approve", "undo")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Id,

    [string]$SandboxRoot = "$env:USERPROFILE\Desktop\Hermes Sandbox"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$localData = [Environment]::GetFolderPath("LocalApplicationData")
$auditPath = Join-Path $localData "LocalAssistantBroker\audit.jsonl"
$statePath = Join-Path $localData "LocalAssistantBroker\action_state.db"

$arguments = @(
    "-3.12", "-m", "local_assistant.broker_admin",
    "--root", $SandboxRoot,
    "--audit", $auditPath,
    "--state", $statePath,
    $Command
)
if ($Id) {
    $arguments += $Id
}

& py @arguments
exit $LASTEXITCODE
