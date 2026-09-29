[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Add-Finding {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Area,
        [Parameter(Mandatory = $true)][string]$Detail
    )
    $script:Findings.Add([PSCustomObject]@{
        Status = $Status
        Area = $Area
        Detail = $Detail
    }) | Out-Null
}

function Write-AuditStep {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ("[CHECK] " + $Message)
}

function Invoke-ReadOnlyNative {
    param(
        [Parameter(Mandatory = $true)][string]$CommandPath,
        [string[]]$Arguments = @(),
        [int]$TimeoutSeconds = 15
    )

    $process = New-Object System.Diagnostics.Process
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $CommandPath
    $startInfo.Arguments = ($Arguments -join " ")
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    $process.StartInfo = $startInfo

    try {
        if (-not $process.Start()) {
            throw "The process could not be started."
        }

        $finished = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $finished) {
            $process.Kill()
            $process.WaitForExit(2000) | Out-Null
            return [PSCustomObject]@{
                ExitCode = -1
                Output = "Timed out after $TimeoutSeconds seconds."
                TimedOut = $true
            }
        }

        $standardOutput = $process.StandardOutput.ReadToEnd().Trim()
        $standardError = $process.StandardError.ReadToEnd().Trim()
        $combinedOutput = @($standardOutput, $standardError) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

        return [PSCustomObject]@{
            ExitCode = $process.ExitCode
            Output = ($combinedOutput -join [Environment]::NewLine)
            TimedOut = $false
        }
    }
    catch {
        return [PSCustomObject]@{
            ExitCode = -1
            Output = $_.Exception.Message
            TimedOut = $false
        }
    }
    finally {
        $process.Dispose()
    }
}

function Test-IsLoopbackAddress {
    param([Parameter(Mandatory = $true)][string]$Address)
    return $Address -in @("127.0.0.1", "::1")
}

$Findings = New-Object System.Collections.Generic.List[object]
$modelInventory = "Not collected"
$runningModels = "Not collected"

Write-Host "Hermes/Ollama Read-Only Audit"
Write-Host "No configuration contents, conversations, credentials, browser data, or personal files are read."
Write-Host "No internet request or system change is performed."
Write-Host ""

Write-AuditStep "Reading PowerShell and Windows version"
Add-Finding "INFO" "PowerShell" "$($PSVersionTable.PSVersion) ($($PSVersionTable.PSEdition))"
Add-Finding "INFO" "Windows" ([Environment]::OSVersion.VersionString)

Write-AuditStep "Checking whether this terminal is elevated"
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdministrator) {
        Add-Finding "WARN" "Privilege" "This PowerShell window is elevated. Close it and run the audit in a normal terminal."
    }
    else {
        Add-Finding "PASS" "Privilege" "Running with a standard user token."
    }
}
catch {
    Add-Finding "WARN" "Privilege" "Could not determine elevation state: $($_.Exception.Message)"
}

Write-AuditStep "Locating Hermes CLI"
$hermesCommand = Get-Command hermes -ErrorAction SilentlyContinue
if ($null -eq $hermesCommand) {
    Add-Finding "INFO" "Hermes CLI" "Not found on PATH. Hermes Desktop may still be installed."
}
else {
    Add-Finding "PASS" "Hermes CLI" "Found: $($hermesCommand.Source)"
    Write-AuditStep "Reading Hermes version (10 second limit)"
    $hermesVersion = Invoke-ReadOnlyNative -CommandPath $hermesCommand.Source -Arguments @("--version") -TimeoutSeconds 10
    if ($hermesVersion.ExitCode -eq 0) {
        Add-Finding "PASS" "Hermes version" $hermesVersion.Output
    }
    elseif ($hermesVersion.TimedOut) {
        Add-Finding "WARN" "Hermes version" $hermesVersion.Output
    }
    else {
        Add-Finding "WARN" "Hermes version" "Command exited $($hermesVersion.ExitCode): $($hermesVersion.Output)"
    }
}

Write-AuditStep "Checking common Hermes directory paths without opening them"
$candidateHermesPaths = @(
    (Join-Path $env:USERPROFILE ".hermes"),
    (Join-Path $env:LOCALAPPDATA "hermes"),
    (Join-Path $env:LOCALAPPDATA "Hermes"),
    (Join-Path $env:LOCALAPPDATA "Programs\Hermes"),
    (Join-Path $env:APPDATA "Hermes")
) | Select-Object -Unique

$existingHermesPaths = @($candidateHermesPaths | Where-Object { Test-Path -LiteralPath $_ })
if ($existingHermesPaths.Count -eq 0) {
    Add-Finding "INFO" "Hermes data" "No common Hermes directory was detected."
}
else {
    Add-Finding "INFO" "Hermes data" ("Detected directory path(s), contents not read: " + ($existingHermesPaths -join "; "))
}

Write-AuditStep "Locating Ollama CLI"
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($null -eq $ollamaCommand) {
    Add-Finding "FAIL" "Ollama CLI" "Not found on PATH."
}
else {
    Add-Finding "PASS" "Ollama CLI" "Found: $($ollamaCommand.Source)"

    Write-AuditStep "Reading Ollama version (15 second limit)"
    $ollamaVersion = Invoke-ReadOnlyNative -CommandPath $ollamaCommand.Source -Arguments @("--version") -TimeoutSeconds 15
    if ($ollamaVersion.ExitCode -eq 0) {
        Add-Finding "PASS" "Ollama version" $ollamaVersion.Output
    }
    else {
        Add-Finding "WARN" "Ollama version" "Command exited $($ollamaVersion.ExitCode): $($ollamaVersion.Output)"
    }

    Write-AuditStep "Reading Ollama model inventory (15 second limit)"
    $ollamaList = Invoke-ReadOnlyNative -CommandPath $ollamaCommand.Source -Arguments @("list") -TimeoutSeconds 15
    if ($ollamaList.ExitCode -eq 0) {
        $modelInventory = $ollamaList.Output
        Add-Finding "PASS" "Model inventory" "Collected model names and sizes from Ollama."
        if ($ollamaList.Output -match "(?m)^local-assistant-brain(?::latest)?\s") {
            Add-Finding "PASS" "Agent model" "local-assistant-brain:latest is available."
        }
        else {
            Add-Finding "WARN" "Agent model" "local-assistant-brain:latest was not found in the model inventory."
        }
    }
    else {
        Add-Finding "WARN" "Model inventory" "ollama list exited $($ollamaList.ExitCode)."
    }

    Write-AuditStep "Reading active Ollama models (15 second limit)"
    $ollamaPs = Invoke-ReadOnlyNative -CommandPath $ollamaCommand.Source -Arguments @("ps") -TimeoutSeconds 15
    if ($ollamaPs.ExitCode -eq 0) {
        $runningModels = $ollamaPs.Output
        Add-Finding "PASS" "Running models" "Collected current processor/context allocation."
    }
    else {
        Add-Finding "WARN" "Running models" "ollama ps exited $($ollamaPs.ExitCode)."
    }

}

Write-AuditStep "Checking the local Ollama API (5 second limit)"
try {
    $ollamaApi = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -Method Get -TimeoutSec 5
    Add-Finding "PASS" "Ollama API" "Loopback API responded with version $($ollamaApi.version)."
}
catch {
    Add-Finding "WARN" "Ollama API" "Loopback API did not respond: $($_.Exception.Message)"
}

Write-AuditStep "Checking whether Ollama listens beyond this PC"
try {
    $listeners = @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction Stop)
    if ($listeners.Count -eq 0) {
        Add-Finding "WARN" "Ollama listener" "No listener was detected on port 11434."
    }
    else {
        $addresses = @($listeners | Select-Object -ExpandProperty LocalAddress -Unique)
        $nonLoopback = @($addresses | Where-Object { -not (Test-IsLoopbackAddress -Address $_) })
        if ($nonLoopback.Count -eq 0) {
            Add-Finding "PASS" "Ollama listener" ("Loopback only: " + ($addresses -join ", "))
        }
        else {
            Add-Finding "FAIL" "Ollama listener" ("Listening beyond loopback: " + ($nonLoopback -join ", ") + ". Do not connect Hermes until corrected.")
        }
    }
}
catch {
    Add-Finding "WARN" "Ollama listener" "Could not inspect port 11434: $($_.Exception.Message)"
}

Write-AuditStep "Checking OLLAMA_HOST without printing a non-local value"
if ([string]::IsNullOrWhiteSpace($env:OLLAMA_HOST)) {
    Add-Finding "INFO" "OLLAMA_HOST" "Not set in this process."
}
elseif ($env:OLLAMA_HOST -match "(^|://)(127\.0\.0\.1|localhost|\[::1\])(?::|$)") {
    Add-Finding "PASS" "OLLAMA_HOST" "Configured for loopback."
}
else {
    Add-Finding "WARN" "OLLAMA_HOST" "A non-loopback value is configured. Its value was intentionally not printed."
}

Write-Host "Findings"
Write-Host "--------"
foreach ($finding in $Findings) {
    Write-Host ("[{0}] {1}: {2}" -f $finding.Status, $finding.Area, $finding.Detail)
}

Write-Host ""
Write-Host "Ollama models"
Write-Host "-------------"
Write-Host $modelInventory

Write-Host ""
Write-Host "Running Ollama models"
Write-Host "---------------------"
Write-Host $runningModels

Write-Host ""
$failedFindings = @($Findings | Where-Object { $_.Status -eq "FAIL" })
if ($failedFindings.Count -gt 0) {
    Write-Host "RESULT: BLOCKED - resolve FAIL findings before connecting Hermes."
    exit 2
}

Write-Host "RESULT: INVENTORY COMPLETE - share this terminal output for review."
exit 0
