param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("list", "add", "remove")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$RootId,

    [Parameter(Position = 2)]
    [string]$Path
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$localData = [Environment]::GetFolderPath("LocalApplicationData")
$configPath = Join-Path $localData "LocalAssistantBroker\inventory_roots.json"

$arguments = @(
    "-3.12", "-m", "local_assistant.inventory_admin",
    "--config", $configPath,
    $Command
)
if ($RootId) {
    $arguments += $RootId
}
if ($Path) {
    $arguments += $Path
}

& py @arguments
exit $LASTEXITCODE
