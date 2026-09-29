param(
    [Parameter(Mandatory = $true)]
    [string]$Root
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$localData = [Environment]::GetFolderPath("LocalApplicationData")
$auditPath = Join-Path $localData "LocalAssistantBroker\audit.jsonl"
$statePath = Join-Path $localData "LocalAssistantBroker\action_state.db"
$inventoryConfigPath = Join-Path $localData "LocalAssistantBroker\inventory_roots.json"
$organizationDestinationPath = Join-Path $localData "LocalAssistantBroker\organization_destinations.json"
$organizationStatePath = Join-Path $localData "LocalAssistantBroker\organization_plan_state.db"
$operatorPermissionsPath = Join-Path $localData "LocalAssistantBroker\operator_permissions.json"
$operatorStatePath = Join-Path $localData "LocalAssistantBroker\operator_state.db"
$operatorQuarantinePath = Join-Path $localData "LocalAssistantBroker\quarantine"
$windowsAppsPath = Join-Path $localData "LocalAssistantBroker\windows_apps.json"

& py -3.12 -m local_assistant.broker_mcp --root $Root --audit $auditPath --state $statePath --inventory-config $inventoryConfigPath --organization-destinations $organizationDestinationPath --organization-state $organizationStatePath --operator-permissions $operatorPermissionsPath --operator-state $operatorStatePath --operator-quarantine $operatorQuarantinePath --windows-apps $windowsAppsPath
exit $LASTEXITCODE
