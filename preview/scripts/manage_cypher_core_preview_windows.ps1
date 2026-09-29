param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("status", "start", "stop", "checkpoint-status", "workflow-status", "failure-status", "forget-checkpoint", "rollback", "uninstall-preview")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "Cypher\CorePreview"
$exePath = Join-Path $installRoot "CypherCoreHost.exe"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$configPath = Join-Path $installRoot "host_config.json"
$stopPath = Join-Path $installRoot "stop.request"
$checkpointPath = Join-Path $installRoot "active-task.json"
$failureReceiptPath = Join-Path $installRoot "last-failure.json"
$workflowCheckpointPath = Join-Path $installRoot "last-workflow.json"
$rollbackShortcut = Join-Path $installRoot "rollback\Local Assistant Host.v063.lnk"
$legacyRoot = Join-Path $env:LOCALAPPDATA "LocalAssistantHost"
$legacyResident = Join-Path $legacyRoot "resident_assistant_windows.ps1"
$legacyManager = Join-Path $legacyRoot "manage_resident_host_windows.ps1"
$startupRoot = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupRoot "Local Assistant Host.lnk"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-PreviewState {
    if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) { return "stopped" }
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        # ConvertFrom-Json can materialize ISO timestamps as DateTime. Casting
        # that value to a culture-formatted string breaks on dd/MM locales.
        $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]$heartbeat.timestamp
        if ($age.TotalSeconds -ge -5 -and $age.TotalSeconds -le 15) { return [string]$heartbeat.status }
    } catch { }
    return "stopped"
}

function Read-CheckpointMetadata {
    if (-not (Test-Path -LiteralPath $checkpointPath -PathType Leaf)) { return $null }
    if ((Get-Item -LiteralPath $checkpointPath).Length -gt 16384) { throw "The recovery checkpoint is oversized and was not read." }
    $value = Get-Content -LiteralPath $checkpointPath -Raw | ConvertFrom-Json
    $allowed = @("schema_version", "run_id", "model_profile", "phase", "state", "started_at_utc", "updated_at_utc", "tool_started", "tool_completed", "tool_failed")
    foreach ($name in $value.PSObject.Properties.Name) {
        if ($name -notin $allowed) { throw "The recovery checkpoint contains an unexpected field and was not displayed." }
    }
    return $value
}

function Read-FailureReceiptMetadata {
    if (-not (Test-Path -LiteralPath $failureReceiptPath -PathType Leaf)) { return $null }
    if ((Get-Item -LiteralPath $failureReceiptPath).Length -gt 8192) { throw "The failure receipt is oversized and was not read." }
    $value = Get-Content -LiteralPath $failureReceiptPath -Raw | ConvertFrom-Json
    $allowed = @("schema_version", "run_id", "model_profile", "failure_stage", "failed_at_utc", "tool_started", "tool_completed", "tool_failed", "response_observed")
    foreach ($name in $value.PSObject.Properties.Name) {
        if ($name -notin $allowed) { throw "The failure receipt contains an unexpected field and was not displayed." }
    }
    if (@($value.PSObject.Properties).Count -ne $allowed.Count) { throw "The failure receipt is missing required metadata and was not displayed." }
    foreach ($name in $allowed) {
        if ($name -notin $value.PSObject.Properties.Name) { throw "The failure receipt is missing required metadata and was not displayed." }
    }
    if ([int]$value.schema_version -ne 1) { throw "The failure receipt schema is unsupported." }
    if ([string]$value.run_id -notmatch '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$') { throw "The failure receipt run ID is invalid." }
    if ([string]$value.model_profile -notin @("fast", "deep")) { throw "The failure receipt model profile is invalid." }
    if ([string]$value.failure_stage -notin @("before_tool", "tool_failed", "tool_incomplete", "after_tool", "response_generation")) { throw "The failure receipt stage is invalid." }
    [void][DateTimeOffset]::Parse([string]$value.failed_at_utc)
    foreach ($count in @($value.tool_started, $value.tool_completed, $value.tool_failed)) {
        if ([int]$count -lt 0 -or [int]$count -gt 10000) { throw "The failure receipt tool counts are invalid." }
    }
    if ($value.response_observed -isnot [bool]) { throw "The failure receipt response flag is invalid." }
    return $value
}

function Read-WorkflowMetadata {
    if (-not (Test-Path -LiteralPath $workflowCheckpointPath -PathType Leaf)) { return $null }
    $item = Get-Item -LiteralPath $workflowCheckpointPath
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $item.Length -gt 4096) {
        throw "The workflow checkpoint is linked or oversized and was not read."
    }
    $value = Get-Content -LiteralPath $workflowCheckpointPath -Raw | ConvertFrom-Json
    $allowed = @("schema_version", "workflow_id", "state", "step_count", "steps_started", "steps_verified", "started_at_utc", "updated_at_utc")
    if (@($value.PSObject.Properties).Count -ne $allowed.Count) { throw "Invalid workflow checkpoint fields." }
    foreach ($name in $allowed) {
        if ($name -cnotin $value.PSObject.Properties.Name) { throw "Invalid workflow checkpoint fields." }
    }
    foreach ($name in @("schema_version", "step_count", "steps_started", "steps_verified")) {
        if ($value.$name -isnot [int] -and $value.$name -isnot [long]) { throw "Invalid workflow checkpoint number." }
    }
    if ($value.schema_version -ne 1 -or [string]$value.workflow_id -cnotmatch '^[a-f0-9]{32}$') { throw "Invalid workflow checkpoint identity." }
    if ([string]$value.state -cnotin @("RUNNING", "COMPLETED", "CANCELLED", "TIMED_OUT", "FAILED", "INTERRUPTED")) { throw "Invalid workflow checkpoint state." }
    if ($value.step_count -lt 1 -or $value.step_count -gt 6 -or $value.steps_started -lt 0 -or
        $value.steps_started -gt $value.step_count -or $value.steps_verified -lt 0 -or
        $value.steps_verified -gt $value.steps_started -or ($value.steps_started - $value.steps_verified) -gt 1) {
        throw "Invalid workflow checkpoint counts."
    }
    if ($value.state -ceq "COMPLETED" -and $value.steps_verified -ne $value.step_count) { throw "Invalid completed workflow checkpoint." }
    $started = [DateTimeOffset]::Parse([string]$value.started_at_utc)
    $updated = [DateTimeOffset]::Parse([string]$value.updated_at_utc)
    if ($updated -lt $started -or $updated -gt [DateTimeOffset]::UtcNow.AddMinutes(5)) { throw "Invalid workflow checkpoint timestamps." }
    return $value
}

function Stop-Preview {
    $state = Get-PreviewState
    if ($state -eq "stopped") { return }
    if ($state -eq "working") { throw "Cypher is handling a task. Finish or stop that task before stopping the host." }
    [IO.File]::WriteAllText($stopPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    do {
        if ((Get-PreviewState) -eq "stopped") {
            Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
            return
        }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Cypher Core Preview did not stop within 15 seconds. If a task is active, open the command center from the tray and stop or resolve it before retrying."
}

function Set-PreviewShortcut {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $exePath
    $shortcut.Arguments = ""
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.Description = "Cypher Core Preview 10.21.0 - hands-free voice preview"
    $shortcut.Save()
}

function Restore-LegacyShortcut {
    if (Test-Path -LiteralPath $rollbackShortcut -PathType Leaf) {
        Copy-Item -LiteralPath $rollbackShortcut -Destination $shortcutPath -Force
        return
    }
    if (-not (Test-Path -LiteralPath $legacyResident -PathType Leaf)) {
        throw "The v0.6.3 resident script is missing, so rollback cannot continue."
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $PSHOME "powershell.exe"
    $shortcut.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $legacyResident + '"'
    $shortcut.WorkingDirectory = $legacyRoot
    $shortcut.Description = "Local Assistant Resident Host v0.6.3"
    $shortcut.Save()
}

function Start-Legacy {
    if (Test-Path -LiteralPath $legacyManager -PathType Leaf) {
        & (Join-Path $PSHOME "powershell.exe") -NoProfile -ExecutionPolicy Bypass -File $legacyManager start
        if ($LASTEXITCODE -ne 0) { throw "The v0.6.3 manager could not restart the rollback host." }
    } elseif (Test-Path -LiteralPath $legacyResident -PathType Leaf) {
        Start-Process -FilePath (Join-Path $PSHOME "powershell.exe") -ArgumentList ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $legacyResident + '"') -WindowStyle Hidden
    } else {
        throw "The v0.6.3 rollback host is missing."
    }
}

switch ($Action) {
    "status" {
        $wakeSetting = "unknown"
        if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            try {
                $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
                $wakeSetting = if ([string]$config.wake_word_enabled -eq "True") { "enabled" } else { "disabled" }
            } catch { }
        }
        Write-Host "Cypher Core Preview: $(Get-PreviewState)"
        Write-Host "Installed: $([bool](Test-Path -LiteralPath $exePath -PathType Leaf))"
        Write-Host "Starts at sign-in: $([bool](Test-Path -LiteralPath $shortcutPath -PathType Leaf))"
        Write-Host "Hermes endpoint: http://127.0.0.1:8642"
        Write-Host "Voice shortcut: Ctrl+Alt+Space"
        Write-Host "Chat shortcut: Ctrl+Win+Alt"
        Write-Host "Default routing: Auto (Qwen fast / GPT-OSS deep)"
        Write-Host "Wake word configured: $wakeSetting"
        Write-Host "Host content logging: disabled"
        Write-Host "Metadata-only task checkpoint: $([bool](Test-Path -LiteralPath $checkpointPath -PathType Leaf))"
        Write-Host "Content-free failure receipt: $([bool](Test-Path -LiteralPath $failureReceiptPath -PathType Leaf))"
        Write-Host "v0.6.3 rollback available: $([bool](Test-Path -LiteralPath $legacyResident -PathType Leaf))"
    }
    "start" {
        if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw "Cypher Core Preview is not installed." }
        if ((Get-PreviewState) -ne "stopped") { Write-Host "Cypher Core Preview is already running."; exit 0 }
        Set-PreviewShortcut
        Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
        Start-Process -FilePath $exePath -WorkingDirectory $installRoot
        Write-Host "Start requested. Press Ctrl+Alt+Space to speak or Ctrl+Win+Alt to open chat."
    }
    "stop" {
        Stop-Preview
        Write-Host "Cypher Core Preview stopped. It will start again at the next sign-in."
    }
    "checkpoint-status" {
        $checkpoint = Read-CheckpointMetadata
        if ($null -eq $checkpoint) { Write-Host "No durable task checkpoint is present."; exit 0 }
        Write-Host "Cypher metadata-only recovery checkpoint"
        Write-Host "Run ID: $($checkpoint.run_id)"
        Write-Host "Model profile: $($checkpoint.model_profile)"
        Write-Host "Phase: $($checkpoint.phase)"
        Write-Host "State: $($checkpoint.state)"
        Write-Host "Started (UTC): $($checkpoint.started_at_utc)"
        Write-Host "Updated (UTC): $($checkpoint.updated_at_utc)"
        Write-Host "Tool events: started=$($checkpoint.tool_started), completed=$($checkpoint.tool_completed), failed=$($checkpoint.tool_failed)"
        Write-Host "No prompt, answer, filename, tool argument, or approval content is stored in this file."
    }
    "failure-status" {
        $receipt = Read-FailureReceiptMetadata
        if ($null -eq $receipt) { Write-Host "No content-free failure receipt is present."; exit 0 }
        Write-Host "Cypher content-free failure receipt"
        Write-Host "Run ID: $($receipt.run_id)"
        Write-Host "Model profile: $($receipt.model_profile)"
        Write-Host "Failure stage: $($receipt.failure_stage)"
        Write-Host "Failed (UTC): $($receipt.failed_at_utc)"
        Write-Host "Tool events: started=$($receipt.tool_started), completed=$($receipt.tool_completed), failed=$($receipt.tool_failed)"
        Write-Host "Response observed: $($receipt.response_observed)"
        Write-Host "No prompt, answer, filename, path, tool argument, approval content, provider error text, or credential is stored in this file."
    }
    "workflow-status" {
        $checkpoint = Read-WorkflowMetadata
        if ($null -eq $checkpoint) { Write-Host "No executed workflow checkpoint is present."; exit 0 }
        Write-Host "Cypher last executed Windows workflow"
        Write-Host "State: $($checkpoint.state)"
        Write-Host "Verified steps: $($checkpoint.steps_verified)/$($checkpoint.step_count)"
        Write-Host "Started steps: $($checkpoint.steps_started)"
        Write-Host "Updated (UTC): $([DateTimeOffset]::Parse([string]$checkpoint.updated_at_utc).ToUniversalTime().ToString('o'))"
        Write-Host "No action was replayed. No text, app names, titles, or reusable approval is stored."
    }
    "forget-checkpoint" {
        if ((Get-PreviewState) -ne "stopped") { throw "Stop Cypher first. An active host may still be reconciling or updating this checkpoint." }
        if (-not (Test-Path -LiteralPath $checkpointPath -PathType Leaf)) { Write-Host "No recovery checkpoint is present."; exit 0 }
        Write-Host "This forgets only Cypher's local recovery metadata. It does not stop or modify any Hermes run."
        Write-Host "Use it only after Hermes can no longer find the run or the checkpoint is invalid."
        $confirmation = Read-Host "Type FORGET RECOVERY CHECKPOINT to continue"
        if ($confirmation -cne "FORGET RECOVERY CHECKPOINT") { Write-Host "Cancelled."; exit 0 }
        Remove-Item -LiteralPath $checkpointPath -Force
        Remove-Item -LiteralPath ($checkpointPath + ".tmp") -Force -ErrorAction SilentlyContinue
        Write-Host "Recovery checkpoint forgotten. No Hermes task was changed."
    }
    "rollback" {
        Write-Host "This stops only the v0.7 preview, restores the v0.6.3 login shortcut, and starts v0.6.3."
        Write-Host "It does not change Hermes, Ollama, broker permissions, models, or personal files."
        $confirmation = Read-Host "Type ROLLBACK TO V0.6.3 to continue"
        if ($confirmation -cne "ROLLBACK TO V0.6.3") { Write-Host "Cancelled."; exit 0 }
        Stop-Preview
        Restore-LegacyShortcut
        Start-Legacy
        Write-Host "Rollback complete. The preview files were preserved for diagnosis or reactivation."
    }
    "uninstall-preview" {
        Write-Host "This removes only Cypher v0.7 Core Preview and restores v0.6.3."
        Write-Host "It does not remove Hermes, Ollama, the capability broker, models, or personal files."
        $confirmation = Read-Host "Type REMOVE CYPHER PREVIEW to continue"
        if ($confirmation -cne "REMOVE CYPHER PREVIEW") { Write-Host "Cancelled."; exit 0 }
        Stop-Preview
        Restore-LegacyShortcut
        Start-Legacy
        $expected = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Cypher\CorePreview"))
        if ([IO.Path]::GetFullPath($installRoot) -ne $expected) { throw "Refusing to remove an unexpected install path." }
        Remove-Item -LiteralPath $installRoot -Recurse -Force
        Write-Host "Cypher Core Preview removed; v0.6.3 is active."
    }
}
