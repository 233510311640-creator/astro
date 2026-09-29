param(
    [Parameter(Position = 0)]
    [ValidateSet("repair", "preflight", "status", "rollback")]
    [string]$Action = "repair"
)

$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "Cypher\CorePreview"
$exePath = Join-Path $installRoot "CypherCoreHost.exe"
$configPath = Join-Path $installRoot "host_config.json"
$tokenPath = Join-Path $installRoot "api_key.bin"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$stopPath = Join-Path $installRoot "stop.request"
$checkpointPath = Join-Path $installRoot "active-task.json"
$backupPath = Join-Path $installRoot "local-runtime-repair-backup.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$settings = @(
    [pscustomobject]@{ key = "model.max_tokens"; value = "16384" },
    [pscustomobject]@{ key = "model.context_length"; value = "65536" },
    [pscustomobject]@{ key = "model.ollama_num_ctx"; value = "65536" },
    [pscustomobject]@{ key = "tools.tool_search.enabled"; value = "on" },
    [pscustomobject]@{ key = "tools.tool_search.listing"; value = "on" }
)
$mcpServerName = "hermes-sandbox"
$expectedReadOnlyToolNames = @(
    "windows_list_apps",
    "mcp__hermes_sandbox__windows_list_apps"
)
$allowedDiscoveryToolNames = @("tool_search", "tool_describe", "tool_call")

function Assert-StandardUser {
    if ($env:OS -ne "Windows_NT") { throw "This helper is only for native Windows." }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this helper from a normal, non-administrator PowerShell window."
    }
}

function Assert-LocalRuntime {
    foreach ($commandName in @("hermes", "ollama")) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "$commandName was not found on PATH."
        }
    }
    foreach ($requiredPath in @($exePath, $configPath, $tokenPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "The installed Cypher Core runtime is incomplete: $requiredPath"
        }
    }
}

function Get-CypherState {
    if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) { return "stopped" }
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse([string]$heartbeat.timestamp)
        if ($age.TotalSeconds -le 15) { return [string]$heartbeat.status }
    } catch { }
    return "stopped"
}

function Assert-NoActiveTask {
    if (Test-Path -LiteralPath $checkpointPath -PathType Leaf) {
        throw "Cypher has an active or unresolved metadata checkpoint. Finish, stop, or resolve that task before changing the local runtime."
    }
    if ((Get-CypherState) -eq "working") {
        throw "Cypher reports an active task. Wait for it to finish or use Stop before continuing."
    }
}

function Stop-CypherCooperatively {
    $state = Get-CypherState
    if ($state -eq "stopped") { return $false }
    if ($state -eq "working") { throw "Cypher is working and was not stopped by this helper." }
    [IO.File]::WriteAllText($stopPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    do {
        if ((Get-CypherState) -eq "stopped") {
            Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
            return $true
        }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Cypher did not stop cooperatively within 20 seconds. No Hermes setting was changed."
}

function Start-CypherAndWait {
    if ((Get-CypherState) -ne "stopped") { return }
    Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $exePath -WorkingDirectory $installRoot
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        if ((Get-CypherState) -ne "stopped") { return }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "The local settings were handled, but Cypher did not publish a fresh heartbeat after restart."
}

function Read-HermesSetting {
    param([string]$Key)
    # Windows PowerShell 5 turns a native program's expected stderr into a
    # NativeCommandError when the script-wide preference is Stop. An unset
    # Hermes key is a normal state, so inspect its exit code without allowing
    # that diagnostic to terminate the repair.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        $raw = @(& hermes config get $Key 2>$null)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $present = ($exitCode -eq 0 -and $raw.Count -gt 0)
    $value = if ($present) { ([string]$raw[-1]).Trim() } else { "" }
    if ([string]::IsNullOrWhiteSpace($value)) { $present = $false; $value = "" }
    return [pscustomobject]@{ present = [bool]$present; value = $value }
}

function Normalize-Confirmation {
    param([AllowNull()][string]$Value)
    # Read-Host can receive trailing whitespace or invisible formatting
    # characters when a confirmation phrase is pasted from chat. Preserve the
    # explicit phrase gate while making equivalent pasted text reliable.
    $normalized = if ($null -eq $Value) { "" } else { [string]$Value }
    $normalized = [regex]::Replace($normalized, "[\u200B\uFEFF]", "")
    $normalized = [regex]::Replace($normalized.Trim(), "\s+", " ")
    return $normalized.ToUpperInvariant()
}

function Get-HermesSettingSnapshot {
    $items = @()
    foreach ($setting in $settings) {
        $current = Read-HermesSetting -Key $setting.key
        $items += [pscustomobject]@{
            key = $setting.key
            present = [bool]$current.present
            value = [string]$current.value
        }
    }
    return @($items)
}

function Set-HermesSettingChecked {
    param([string]$Key, [string]$Value)
    & hermes config set $Key $Value | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Hermes rejected configuration key '$Key'." }
}

function Restore-HermesSnapshot {
    param([object[]]$Snapshot)
    foreach ($item in @($Snapshot)) {
        if ([bool]$item.present) {
            & hermes config set ([string]$item.key) ([string]$item.value) | Out-Host
        } else {
            & hermes config unset ([string]$item.key) | Out-Host
        }
        if ($LASTEXITCODE -ne 0) { throw "Could not restore Hermes key '$($item.key)'." }
    }
}

function Write-PersistentBackup {
    param([object[]]$Snapshot)
    $record = [ordered]@{
        schema_version = 1
        created_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
        settings = @($Snapshot)
    }
    [IO.File]::WriteAllText($backupPath, ($record | ConvertTo-Json -Depth 5), $utf8NoBom)
}

function Read-PersistentBackup {
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        throw "No Cypher local-runtime rollback backup is present."
    }
    if ((Get-Item -LiteralPath $backupPath).Length -gt 32768) {
        throw "The Cypher local-runtime rollback backup is unexpectedly large."
    }
    $record = Get-Content -LiteralPath $backupPath -Raw | ConvertFrom-Json
    if ([int]$record.schema_version -ne 1 -or @($record.settings).Count -ne $settings.Count) {
        throw "The Cypher local-runtime rollback backup has an unsupported format."
    }
    $expected = @($settings | ForEach-Object { $_.key })
    foreach ($item in @($record.settings)) {
        if ([string]$item.key -notin $expected -or $item.present -isnot [bool]) {
            throw "The Cypher local-runtime rollback backup contains an unexpected setting."
        }
    }
    return @($record.settings)
}

function Get-LocalHostConfiguration {
    if ((Get-Item -LiteralPath $configPath).Length -gt 65536) { throw "Cypher host_config.json is unexpectedly large." }
    $hostConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $model = if ([string]::IsNullOrWhiteSpace([string]$hostConfig.fast_model)) { "qwen3.5:9b-q4_K_M" } else { ([string]$hostConfig.fast_model).Trim() }
    if ($model -notmatch '^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63})?$') {
        throw "Cypher's fast-model assignment is invalid."
    }
    $endpointText = if ([string]::IsNullOrWhiteSpace([string]$hostConfig.endpoint)) { "http://127.0.0.1:8642" } else { ([string]$hostConfig.endpoint).Trim() }
    $endpoint = [Uri]$endpointText
    if ($endpoint.Scheme -ne "http" -or $endpoint.Host.ToLowerInvariant() -notin @("127.0.0.1", "localhost", "::1") -or
        -not [string]::IsNullOrEmpty($endpoint.UserInfo) -or -not [string]::IsNullOrEmpty($endpoint.Query) -or
        -not [string]::IsNullOrEmpty($endpoint.Fragment) -or $endpoint.AbsolutePath -notin @("", "/")) {
        throw "Cypher is not configured for a plain loopback Hermes endpoint."
    }
    return [pscustomobject]@{ model = $model; endpoint = $endpoint }
}

function Get-ProtectedApiKey {
    Add-Type -AssemblyName System.Security
    $protectedBase64 = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
    $protectedBytes = [Convert]::FromBase64String($protectedBase64)
    $plainBytes = $null
    try {
        $plainBytes = [Security.Cryptography.ProtectedData]::Unprotect(
            $protectedBytes,
            $null,
            [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [Text.Encoding]::UTF8.GetString($plainBytes)
    } finally {
        if ($plainBytes) { [Array]::Clear($plainBytes, 0, $plainBytes.Length) }
        if ($protectedBytes) { [Array]::Clear($protectedBytes, 0, $protectedBytes.Length) }
    }
}

function Restart-HermesGateway {
    & hermes gateway restart | Out-Host
    if ($LASTEXITCODE -ne 0) {
        & hermes gateway start | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Hermes gateway could not be restarted." }
    }
}

function Wait-HermesRunsApi {
    param([Uri]$Endpoint, [string]$ApiKey)
    $headers = @{ Authorization = "Bearer $ApiKey" }
    $deadline = [DateTime]::UtcNow.AddSeconds(75)
    do {
        try {
            $capabilities = Invoke-RestMethod -Uri ([Uri]::new($Endpoint, "/v1/capabilities")) -Headers $headers -Method Get -TimeoutSec 3
            if ($capabilities.features.run_submission -eq $true -and $capabilities.features.run_events_sse -eq $true) { return }
        } catch { }
        Start-Sleep -Milliseconds 750
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "The authenticated loopback Hermes Runs API did not become healthy."
}

function Invoke-BoundedHermesMcpProbe {
    param([int]$TimeoutSeconds = 45)
    $hermesCommand = Get-Command hermes -ErrorAction Stop
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = [string]$hermesCommand.Source
    $psi.Arguments = "mcp test $mcpServerName"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    try {
        if (-not $process.Start()) { throw "Hermes's bounded MCP probe could not start." }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            try { $process.Kill() } catch { }
            try { $process.WaitForExit(5000) | Out-Null } catch { }
            throw "The bounded Hermes MCP probe exceeded $TimeoutSeconds seconds and was stopped."
        }
        $stdout = [string]$stdoutTask.GetAwaiter().GetResult()
        $stderr = [string]$stderrTask.GetAwaiter().GetResult()
        $combined = $stdout + "`n" + $stderr
        if ($process.ExitCode -ne 0) { throw "Hermes could not connect to the Cypher MCP broker." }
        $countMatch = [regex]::Match($combined, "Tools\s+discovered\s*:\s*(\d+)", [Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $countMatch.Success -or [int]$countMatch.Groups[1].Value -lt 1) {
            throw "Hermes's MCP probe did not report any discovered tools."
        }
        if ($combined.IndexOf("windows_list_apps", [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw "The Cypher MCP broker did not advertise windows_list_apps."
        }
        Write-Host "[PASS] Bounded MCP probe found windows_list_apps ($($countMatch.Groups[1].Value) broker tools discovered)."
    } finally {
        if ($process) { $process.Dispose() }
    }
}

function Get-EventEvidence {
    param([string]$SseText)
    $startedNames = New-Object System.Collections.Generic.List[string]
    $completedNames = New-Object System.Collections.Generic.List[string]
    $completionErrors = New-Object System.Collections.Generic.List[string]
    foreach ($block in [regex]::Split(($SseText.Trim()), "\r?\n\r?\n")) {
        if ([string]::IsNullOrWhiteSpace($block)) { continue }
        $eventName = "message"
        $dataLines = New-Object System.Collections.Generic.List[string]
        foreach ($line in ($block -split "\r?\n")) {
            if ($line.StartsWith("event:")) { $eventName = $line.Substring(6).Trim() }
            if ($line.StartsWith("data:")) { $dataLines.Add($line.Substring(5).TrimStart()) }
        }
        $data = $null
        if ($dataLines.Count -gt 0) {
            try { $data = (($dataLines -join "`n") | ConvertFrom-Json) } catch { }
        }
        $embeddedType = if ($data -and $data.PSObject.Properties.Name -contains "type") { [string]$data.type } else { "" }
        $embeddedEvent = if ($data -and $data.PSObject.Properties.Name -contains "event") { [string]$data.event } else { "" }
        $effectiveName = ($eventName + " " + $embeddedType + " " + $embeddedEvent).ToLowerInvariant()
        if ($effectiveName.Contains("tool") -and ($effectiveName.Contains("start") -or $effectiveName.Contains("started"))) {
            $toolName = ""
            foreach ($propertyName in @("name", "tool_name", "tool")) {
                if ($data -and $data.PSObject.Properties.Name -contains $propertyName) {
                    $rawCandidate = $data.$propertyName
                    $candidate = if ($rawCandidate -is [string]) {
                        [string]$rawCandidate
                    } elseif ($rawCandidate -and $rawCandidate.PSObject.Properties.Name -contains "name") {
                        [string]$rawCandidate.name
                    } else { "" }
                    if (-not [string]::IsNullOrWhiteSpace($candidate)) { $toolName = $candidate.Trim(); break }
                }
            }
            $startedNames.Add($toolName)
        }
        if ($effectiveName.Contains("tool") -and ($effectiveName.Contains("complete") -or $effectiveName.Contains("completed"))) {
            $completedToolName = ""
            foreach ($propertyName in @("name", "tool_name", "tool")) {
                if ($data -and $data.PSObject.Properties.Name -contains $propertyName) {
                    $rawCandidate = $data.$propertyName
                    $candidate = if ($rawCandidate -is [string]) {
                        [string]$rawCandidate
                    } elseif ($rawCandidate -and $rawCandidate.PSObject.Properties.Name -contains "name") {
                        [string]$rawCandidate.name
                    } else { "" }
                    if (-not [string]::IsNullOrWhiteSpace($candidate)) { $completedToolName = $candidate.Trim(); break }
                }
            }
            $completedNames.Add($completedToolName)
            if ($data -and $data.PSObject.Properties.Name -contains "error" -and $null -ne $data.error) {
                $errorText = ([string]$data.error).Trim()
                if (-not [string]::IsNullOrWhiteSpace($errorText) -and $errorText.ToLowerInvariant() -notin @("false", "none", "null")) {
                    $completionErrors.Add($errorText.Substring(0, [Math]::Min(160, $errorText.Length)))
                }
            }
        }
    }
    return [pscustomobject]@{
        started_names = @($startedNames)
        completed_names = @($completedNames)
        completion_errors = @($completionErrors)
    }
}

function Test-IsExpectedWindowsListAppsToolName {
    param([AllowNull()][string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    $normalized = $Name.Trim().ToLowerInvariant()
    return ($normalized -in @($expectedReadOnlyToolNames | ForEach-Object { $_.ToLowerInvariant() }))
}

function Test-IsAllowedPreflightToolName {
    param([AllowNull()][string]$Name)
    if (Test-IsExpectedWindowsListAppsToolName -Name $Name) { return $true }
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    return ($Name.Trim().ToLowerInvariant() -in $allowedDiscoveryToolNames)
}

function Invoke-LocalRuntimePreflight {
    param([Uri]$Endpoint, [string]$ApiKey, [string]$Model)
    & ollama show $Model *> $null
    if ($LASTEXITCODE -ne 0) { throw "Cypher's fast model is not available to Ollama: $Model" }

    Invoke-BoundedHermesMcpProbe
    Write-Host "[CHECK] Starting one fresh Hermes run through the bounded discovery bridge and read-only windows_list_apps tool."
    $headers = @{ Authorization = "Bearer $ApiKey" }
    $sentinel = "CYPHER_RUNTIME_PREFLIGHT_OK"
    $payload = [ordered]@{
        input = "List my registered Windows applications without launching, focusing, or changing anything. Use the read-only windows_list_apps capability. If Hermes exposes progressive-disclosure tools, find or describe it only as needed and invoke the exact returned schema through tool_call. Its canonical wire name is mcp__hermes_sandbox__windows_list_apps. After that read-only tool succeeds, reply exactly CYPHER_RUNTIME_PREFLIGHT_OK."
        instructions = "This is a fresh, single-turn local runtime preflight. There is no prior response and nothing to resume. The current request is authoritative. The only permitted auxiliary calls are tool_search, tool_describe, and tool_call, and the only permitted underlying capability is windows_list_apps (canonical mcp__hermes_sandbox__windows_list_apps). Copy tool names verbatim. Do not call any launch, focus, terminal, file-write, or other tool. Return the sentinel only after the read-only tool completes successfully."
        session_id = "cypher-runtime-preflight-" + [Guid]::NewGuid().ToString("N")
        provider = "custom"
        model = $Model
        model_options = @{}
    }
    $run = Invoke-RestMethod -Uri ([Uri]::new($Endpoint, "/v1/runs")) -Headers $headers -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 5) -TimeoutSec 15
    $runId = [string]$run.run_id
    if ($runId -notmatch '^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$') { throw "Hermes returned an invalid preflight run ID." }

    Add-Type -AssemblyName System.Net.Http
    $http = New-Object System.Net.Http.HttpClient
    $eventResponse = $null
    $readTask = $null
    try {
        $http.Timeout = [TimeSpan]::FromMinutes(6)
        $http.DefaultRequestHeaders.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $ApiKey)
        $eventResponse = $http.GetAsync(([Uri]::new($Endpoint, "/v1/runs/$runId/events")), [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        if (-not $eventResponse.IsSuccessStatusCode) { throw "Hermes refused the preflight event stream." }
        $readTask = $eventResponse.Content.ReadAsStringAsync()

        $terminal = $null
        $deadline = [DateTime]::UtcNow.AddMinutes(5)
        $startedAt = [DateTime]::UtcNow
        $nextProgress = $startedAt.AddSeconds(15)
        do {
            Start-Sleep -Milliseconds 500
            $terminal = Invoke-RestMethod -Uri ([Uri]::new($Endpoint, "/v1/runs/$runId")) -Headers $headers -Method Get -TimeoutSec 5
            $state = ([string]$terminal.status).ToLowerInvariant()
            if ($state -in @("completed", "failed", "cancelled")) { break }
            if ([DateTime]::UtcNow -ge $nextProgress) {
                $elapsedSeconds = [int]([DateTime]::UtcNow - $startedAt).TotalSeconds
                Write-Host "[CHECK] Live preflight still running ($elapsedSeconds seconds; 300-second limit)."
                $nextProgress = [DateTime]::UtcNow.AddSeconds(15)
            }
        } while ([DateTime]::UtcNow -lt $deadline)

        if ($state -notin @("completed", "failed", "cancelled")) {
            try { Invoke-RestMethod -Uri ([Uri]::new($Endpoint, "/v1/runs/$runId/stop")) -Headers $headers -Method Post -ContentType "application/json" -Body "{}" -TimeoutSec 8 | Out-Null } catch { }
            throw "The local runtime preflight timed out and was stopped."
        }
        if ($state -ne "completed") { throw "The local runtime preflight ended with Hermes state '$state'." }
        if (-not $readTask.Wait(15000)) { throw "Hermes completed the run but did not close its event stream." }

        $evidence = Get-EventEvidence -SseText $readTask.Result
        $started = @($evidence.started_names)
        if ($started.Count -lt 1) {
            throw "Hermes completed the preflight without starting a tool. The model did not use Cypher's discovery bridge."
        }
        $unexpected = @($started | Where-Object { -not (Test-IsAllowedPreflightToolName -Name $_) })
        if ($unexpected.Count -gt 0) {
            throw "The preflight attempted an unexpected tool: $($unexpected[0])"
        }
        if (@($started | Where-Object { Test-IsExpectedWindowsListAppsToolName -Name $_ }).Count -lt 1) {
            throw "Hermes used discovery but never started the exact windows_list_apps capability."
        }
        $completed = @($evidence.completed_names)
        if (@($completed | Where-Object { Test-IsExpectedWindowsListAppsToolName -Name $_ }).Count -lt 1) {
            throw "The preflight did not complete the exact windows_list_apps capability."
        }
        if (@($evidence.completion_errors).Count -gt 0) {
            throw "Hermes reported a tool-completion error during the read-only preflight."
        }

        $output = [string]$terminal.output
        if ($output -notmatch [regex]::Escape($sentinel)) { throw "The preflight did not return its success sentinel." }
        foreach ($contamination in @(
            "previous response", "truncated response", "cut off", "resume from", "continue exactly",
            "previous context", "what were we working on", "what task or question"
        )) {
            if ($output.IndexOf($contamination, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
                throw "Hermes still produced false continuation text ('$contamination')."
            }
        }
        Write-Host "[PASS] Fresh Hermes run reached and completed windows_list_apps without launching anything."
        Write-Host "[PASS] No false previous-response or truncation recovery text was observed."
    } finally {
        if ($eventResponse) { $eventResponse.Dispose() }
        if ($http) { $http.Dispose() }
    }
}

function Show-Status {
    Write-Host "Cypher Local Runtime Repair status"
    Write-Host "Cypher host: $(Get-CypherState)"
    Write-Host "Rollback backup present: $([bool](Test-Path -LiteralPath $backupPath -PathType Leaf))"
    foreach ($setting in $settings) {
        $current = Read-HermesSetting -Key $setting.key
        $value = if ($current.present) { [string]$current.value } else { "<unset>" }
        Write-Host "$($setting.key): $value"
    }
    Write-Host "This status view does not run a model or read application/file content."
}

Assert-StandardUser
Assert-LocalRuntime

if ($Action -eq "status") { Show-Status; exit 0 }

Assert-NoActiveTask
$runtime = Get-LocalHostConfiguration
$apiKey = Get-ProtectedApiKey
$wasRunning = ((Get-CypherState) -ne "stopped")

try {
    if ($Action -eq "preflight") {
        Wait-HermesRunsApi -Endpoint $runtime.endpoint -ApiKey $apiKey
        Invoke-LocalRuntimePreflight -Endpoint $runtime.endpoint -ApiKey $apiKey -Model $runtime.model
        exit 0
    }

    if ($Action -eq "rollback") {
        $confirmation = Read-Host "Type ROLLBACK CYPHER LOCAL RUNTIME to restore the saved Hermes settings"
        if ((Normalize-Confirmation -Value $confirmation) -ne "ROLLBACK CYPHER LOCAL RUNTIME") {
            Write-Host "Cancelled. No setting changed."
            exit 2
        }
        [void](Stop-CypherCooperatively)
        Restore-HermesSnapshot -Snapshot (Read-PersistentBackup)
        Restart-HermesGateway
        Wait-HermesRunsApi -Endpoint $runtime.endpoint -ApiKey $apiKey
        Remove-Item -LiteralPath $backupPath -Force
        if ($wasRunning) { Start-CypherAndWait }
        Write-Host "[PASS] The saved pre-repair Hermes settings were restored."
        exit 0
    }

    Write-Host "Cypher v0.8.3 Local Runtime Repair 7"
    Write-Host "This adjusts only local Hermes model output/context limits and bounded MCP discovery."
    Write-Host "It does not update Hermes, download/delete models, clear caches, widen file permissions, or launch an application."
    Write-Host "A bounded broker probe and live read-only windows_list_apps run must pass before success is reported."
    Write-Host ""
    $confirmation = Read-Host "Type REPAIR CYPHER LOCAL RUNTIME to continue"
    if ((Normalize-Confirmation -Value $confirmation) -ne "REPAIR CYPHER LOCAL RUNTIME") {
        Write-Host "Cancelled. No setting changed."
        exit 2
    }

    $attemptSnapshot = Get-HermesSettingSnapshot
    $createdBackup = $false
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        Write-PersistentBackup -Snapshot $attemptSnapshot
        $createdBackup = $true
    }
    [void](Stop-CypherCooperatively)
    try {
        foreach ($setting in $settings) { Set-HermesSettingChecked -Key $setting.key -Value $setting.value }
        Restart-HermesGateway
        Wait-HermesRunsApi -Endpoint $runtime.endpoint -ApiKey $apiKey
        Invoke-LocalRuntimePreflight -Endpoint $runtime.endpoint -ApiKey $apiKey -Model $runtime.model
        if ($wasRunning) { Start-CypherAndWait }
        Write-Host ""
        Write-Host "[PASS] Cypher's local Hermes runtime repair is verified."
        Write-Host "Open Cypher with Ctrl+Alt+Space and retry: List my registered Windows applications. Do not launch anything."
    } catch {
        Write-Warning "The live preflight did not pass. Restoring every setting from before this attempt."
        Restore-HermesSnapshot -Snapshot $attemptSnapshot
        Restart-HermesGateway
        Wait-HermesRunsApi -Endpoint $runtime.endpoint -ApiKey $apiKey
        if ($createdBackup) { Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue }
        if ($wasRunning) { Start-CypherAndWait }
        throw
    }
} finally {
    $apiKey = $null
}
