param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("destinations", "add-destination", "remove-destination", "plans", "show", "review", "reject")]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Value,

    [Parameter(Position = 2)]
    [string]$Path
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$localData = [Environment]::GetFolderPath("LocalApplicationData")
$inventoryConfig = Join-Path $localData "LocalAssistantBroker\inventory_roots.json"
$destinationConfig = Join-Path $localData "LocalAssistantBroker\organization_destinations.json"
$statePath = Join-Path $localData "LocalAssistantBroker\organization_plan_state.db"
$auditPath = Join-Path $localData "LocalAssistantBroker\audit.jsonl"

$arguments = @(
    "-3.12", "-m", "local_assistant.organization_admin",
    "--inventory-config", $inventoryConfig,
    "--destination-config", $destinationConfig,
    "--state", $statePath,
    "--audit", $auditPath,
    $Command
)
if ($Value) {
    $arguments += $Value
}
if ($Path) {
    $arguments += $Path
}

& py @arguments
exit $LASTEXITCODE
