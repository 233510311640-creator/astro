$ErrorActionPreference = "Stop"

$installRoot = Join-Path $env:LOCALAPPDATA "Cypher\CorePreview"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$checkpointPath = Join-Path $installRoot "active-task.json"

Write-Host "Cypher/Hermes Bounded Tool-Discovery Configuration"
Write-Host "This changes only tools.tool_search.enabled and tools.tool_search.listing in the current Hermes profile and restarts the local gateway."
Write-Host "It does not add authority, change broker roots, read file contents, change models, or enable built-in terminal/file tools."
Write-Host ""

if ($env:OS -ne "Windows_NT") { throw "This configuration helper is only for native Windows." }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this helper from a normal, non-administrator PowerShell window."
}
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) { throw "Hermes CLI was not found on PATH." }

if (Test-Path -LiteralPath $checkpointPath -PathType Leaf) {
    throw "Cypher has a metadata checkpoint for an active or unresolved run. Resolve or stop that run before restarting Hermes."
}
if (Test-Path -LiteralPath $heartbeatPath -PathType Leaf) {
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]$heartbeat.timestamp
        if ($age.TotalSeconds -ge -5 -and $age.TotalSeconds -le 15 -and [string]$heartbeat.status -eq "working") {
            throw "Cypher reports an active task. Wait for it to finish or use Stop before restarting Hermes."
        }
    } catch {
        if ($_.Exception.Message -like "Cypher reports an active task*") { throw }
    }
}

function Read-HermesSetting {
    param([string]$Key)
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        $raw = @(& hermes config get $Key 2>$null)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $present = ($exitCode -eq 0 -and $raw.Count -gt 0)
    $value = if ($present) { ([string]$raw[-1]).Trim().ToLowerInvariant() } else { "" }
    if ([string]::IsNullOrWhiteSpace($value)) { $present = $false; $value = "" }
    return [pscustomobject]@{ present = [bool]$present; value = $value }
}

$previousEnabled = Read-HermesSetting -Key "tools.tool_search.enabled"
$previousListing = Read-HermesSetting -Key "tools.tool_search.listing"
$enabledDisplay = if ($previousEnabled.present) { $previousEnabled.value } else { "auto (default/unset)" }
$listingDisplay = if ($previousListing.present) { $previousListing.value } else { "auto (default/unset)" }
Write-Host "Current Hermes tool-search mode: $enabledDisplay"
Write-Host "Current Hermes tool-name listing mode: $listingDisplay"

if ($previousEnabled.value -eq "on" -and $previousListing.value -eq "on") {
    Write-Host "[PASS] Bounded MCP discovery is already configured."
    & hermes mcp test hermes-sandbox
    if ($LASTEXITCODE -ne 0) { throw "The hermes-sandbox MCP server did not pass its connection test." }
    exit 0
}

Write-Host ""
Write-Host "Current Hermes builds can hide connected MCP tools when tool search is disabled."
Write-Host "Cypher will enable the bounded discovery bridge and its exact-name listing."
$confirmation = Read-Host "Type CONFIGURE BOUNDED CYPHER TOOLS to continue"
if ($confirmation -cne "CONFIGURE BOUNDED CYPHER TOOLS") { Write-Host "Cancelled. No configuration changed."; exit 0 }

function Restore-HermesSetting {
    param([string]$Key, [object]$Snapshot)
    if ($Snapshot.present) {
        & hermes config set $Key ([string]$Snapshot.value) | Out-Host
    } else {
        & hermes config unset $Key | Out-Host
    }
}

function Restore-PreviousModes {
    Restore-HermesSetting -Key "tools.tool_search.enabled" -Snapshot $previousEnabled
    Restore-HermesSetting -Key "tools.tool_search.listing" -Snapshot $previousListing
}

try {
    & hermes config set tools.tool_search.enabled on | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Hermes rejected the bounded tool-search configuration." }
    & hermes config set tools.tool_search.listing on | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Hermes rejected the bounded tool-name listing configuration." }

    & hermes gateway restart | Out-Host
    if ($LASTEXITCODE -ne 0) {
        & hermes gateway start | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Hermes gateway could not be restarted." }
    }
    Start-Sleep -Seconds 2

    & hermes mcp test hermes-sandbox | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "The hermes-sandbox MCP server did not pass its post-change connection test." }

    Write-Host ""
    Write-Host "[PASS] Hermes now exposes Cypher's bounded MCP tools through exact-name discovery."
    Write-Host "No permission or root changed. Reopen Cypher with Ctrl+Alt+Space and retry the proposal-only operator test."
} catch {
    Write-Warning "Bounded tool-discovery configuration did not complete. Restoring both previous tool-search settings."
    Restore-PreviousModes
    & hermes gateway restart | Out-Host
    throw
}
