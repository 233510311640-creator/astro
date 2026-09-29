param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("list", "seed-builtins", "add", "remove", "set-text-entry", "set-app-user-model-id")]
    [string]$Action,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArguments
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$localData = [Environment]::GetFolderPath("LocalApplicationData")
$windowsAppsPath = Join-Path $localData "LocalAssistantBroker\windows_apps.json"

& py -3.12 -m local_assistant.windows_admin --config $windowsAppsPath $Action @CommandArguments
exit $LASTEXITCODE
