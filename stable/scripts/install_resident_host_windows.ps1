param(
    [ValidatePattern("^[A-Za-z0-9 _-]{1,32}$")]
    [string]$AssistantName = "Hermes"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$installRoot = Join-Path $env:LOCALAPPDATA "LocalAssistantHost"
$hermesRoot = Join-Path $env:LOCALAPPDATA "hermes"
$hermesEnvPath = Join-Path $hermesRoot ".env"
$startupRoot = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupRoot "Local Assistant Host.lnk"
$residentSource = Join-Path $PSScriptRoot "resident_assistant_windows.ps1"
$residentTarget = Join-Path $installRoot "resident_assistant_windows.ps1"
$managerSource = Join-Path $PSScriptRoot "manage_resident_host_windows.ps1"
$managerTarget = Join-Path $installRoot "manage_resident_host_windows.ps1"
$configPath = Join-Path $installRoot "host_config.json"
$tokenPath = Join-Path $installRoot "api_key.dpapi"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$stopRequestPath = Join-Path $installRoot "stop.request"
$managedBegin = "# BEGIN LOCAL_ASSISTANT_HOST_V0_6"
$managedEnd = "# END LOCAL_ASSISTANT_HOST_V0_6"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Write-Host "Local Windows Assistant Resident Host v0.6.3"
Write-Host "This installer enables Hermes' loopback API, installs its login gateway, and adds a hidden per-user tray host."
Write-Host "Hermes may request one Windows UAC approval to create its Scheduled Task. The resident host itself does not run as administrator."
Write-Host "This package does not enable Hermes built-in tools, enable a microphone, or weaken the capability broker."
Write-Host ""

if ($env:OS -ne "Windows_NT") {
    throw "This installer is only for native Windows."
}
if (-not (Test-Path -LiteralPath $residentSource -PathType Leaf) -or
    -not (Test-Path -LiteralPath $managerSource -PathType Leaf)) {
    throw "Resident host package files are incomplete. Extract the whole ZIP into one folder."
}

function Resolve-HermesPath {
    $command = Get-Command "hermes.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\bin\hermes.exe"),
        (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe")
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    throw "Hermes CLI was not found. Install or repair Hermes before installing the resident host."
}

function New-ApiKey {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

function Get-ManagedApiKey {
    param([string]$Content)
    $pattern = "(?ms)^" + [regex]::Escape($managedBegin) + "\r?\n(.*?)^" + [regex]::Escape($managedEnd) + "\r?\n?"
    $match = [regex]::Match($Content, $pattern)
    if (-not $match.Success) {
        return $null
    }
    $keyMatch = [regex]::Match($match.Groups[1].Value, "(?im)^API_SERVER_KEY\s*=\s*([A-Fa-f0-9]{64})\s*$")
    if ($keyMatch.Success) {
        return $keyMatch.Groups[1].Value
    }
    return $null
}

function Set-ManagedHermesApiBlock {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$ApiKey
    )

    if (-not (Test-Path -LiteralPath $hermesRoot -PathType Container)) {
        throw "Hermes data folder was not found at $hermesRoot."
    }
    $existing = if (Test-Path -LiteralPath $Path -PathType Leaf) {
        Get-Content -LiteralPath $Path -Raw
    } else {
        ""
    }
    $pattern = "(?ms)^" + [regex]::Escape($managedBegin) + "\r?\n.*?^" + [regex]::Escape($managedEnd) + "\r?\n?"
    $withoutManagedBlock = [regex]::Replace($existing, $pattern, "").TrimEnd()
    if ($withoutManagedBlock -match "(?im)^\s*API_SERVER_(ENABLED|HOST|PORT|KEY)\s*=") {
        throw "Existing API_SERVER_* settings were found outside the resident host's managed block. The installer will not overwrite them."
    }

    $backupPath = Join-Path $hermesRoot ".env.pre-local-assistant-host-v0.6.bak"
    if ((Test-Path -LiteralPath $Path -PathType Leaf) -and -not (Test-Path -LiteralPath $backupPath)) {
        Copy-Item -LiteralPath $Path -Destination $backupPath
    }

    $block = @(
        $managedBegin,
        "API_SERVER_ENABLED=true",
        "API_SERVER_HOST=127.0.0.1",
        "API_SERVER_PORT=8642",
        "API_SERVER_KEY=$ApiKey",
        $managedEnd
    ) -join [Environment]::NewLine
    $newContent = if ([string]::IsNullOrWhiteSpace($withoutManagedBlock)) {
        $block + [Environment]::NewLine
    } else {
        $withoutManagedBlock + [Environment]::NewLine + [Environment]::NewLine + $block + [Environment]::NewLine
    }
    [IO.File]::WriteAllText($Path, $newContent, $utf8NoBom)
}

function Test-HermesGatewayInstalled {
    $schtasksPath = Join-Path $env:SystemRoot "System32\schtasks.exe"
    if (Test-Path -LiteralPath $schtasksPath -PathType Leaf) {
        foreach ($taskName in @("Hermes_Gateway", "HermesGateway")) {
            & $schtasksPath /Query /TN $taskName 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return $true
            }
        }
    }

    if (Test-Path -LiteralPath $startupRoot -PathType Container) {
        $startupEntry = Get-ChildItem -LiteralPath $startupRoot -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "(?i)(hermes.*gateway|gateway.*hermes)" } |
            Select-Object -First 1
        if ($startupEntry) {
            return $true
        }
    }
    return $false
}

function Wait-HermesApi {
    param([ValidateRange(1, 300)][int]$TimeoutSeconds = 120)

    $healthUri = "http://127.0.0.1:8642/health"
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Uri $healthUri -Method Get -TimeoutSec 2
            if ($health.status -eq "ok") {
                return $true
            }
        } catch {
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Stop-ExistingResidentHost {
    if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) {
        return
    }
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        $heartbeatAge = [DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse([string]$heartbeat.timestamp)
        if ($heartbeatAge.TotalSeconds -gt 15) {
            return
        }
    } catch {
        return
    }

    Write-Host "[INFO] Stopping the existing resident host cooperatively before upgrading its interface."
    [IO.File]::WriteAllText($stopRequestPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    do {
        if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) {
            Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
            Write-Host "[PASS] Existing resident host stopped cleanly."
            return
        }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "The existing resident host did not stop within 15 seconds. Exit it from the tray icon and run this installer again."
}

$pythonVersion = & py -3.12 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 is required for the packaged validation tests."
}
Write-Host "[PASS] $pythonVersion"

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    $installTestPatterns = @(
        "test_approved_actions.py",
        "test_broker_windows_scripts.py",
        "test_capability_broker.py",
        "test_hermes_audit_script.py",
        "test_inventory_broker.py",
        "test_local_model.py",
        "test_organization_planner.py",
        "test_resident_host_windows_scripts.py"
    )
    foreach ($testPattern in $installTestPatterns) {
        & py -3.12 -m unittest discover -s (Join-Path $projectRoot "tests") -p $testPattern -v
        if ($LASTEXITCODE -ne 0) {
            throw "Required test file failed: $testPattern. The resident host was not installed."
        }
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$hermesPath = Resolve-HermesPath
$originalHermesEnvExists = Test-Path -LiteralPath $hermesEnvPath -PathType Leaf
$existingEnv = if ($originalHermesEnvExists) {
    Get-Content -LiteralPath $hermesEnvPath -Raw
} else {
    ""
}
$apiKey = Get-ManagedApiKey -Content $existingEnv
if (-not $apiKey) {
    $apiKey = New-ApiKey
}

Stop-ExistingResidentHost
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
Copy-Item -LiteralPath $residentSource -Destination $residentTarget -Force
Copy-Item -LiteralPath $managerSource -Destination $managerTarget -Force

$secureKey = ConvertTo-SecureString -String $apiKey -AsPlainText -Force
$protectedKey = $secureKey | ConvertFrom-SecureString
[IO.File]::WriteAllText($tokenPath, $protectedKey, $utf8NoBom)

$settings = [ordered]@{
    version = "0.6.3"
    assistant_name = $AssistantName
    endpoint = "http://127.0.0.1:8642"
    conversation = "resident-main"
    activation = "Ctrl+Alt+Space"
    microphone_enabled = $false
    content_logging = $false
}
[IO.File]::WriteAllText($configPath, ($settings | ConvertTo-Json -Depth 8), $utf8NoBom)
Set-ManagedHermesApiBlock -Path $hermesEnvPath -ApiKey $apiKey
$gatewayWasInstalled = Test-HermesGatewayInstalled

try {
    if ($gatewayWasInstalled) {
        Write-Host "[INFO] An existing Hermes gateway registration was found. Restarting it so the loopback API settings take effect."
        & $hermesPath gateway restart
        if ($LASTEXITCODE -ne 0) {
            throw "Hermes gateway restart failed. Review the Hermes output above."
        }
    } else {
        Write-Host "[INFO] Installing Hermes gateway autostart. Hermes may request one UAC approval to create its Scheduled Task."
        & $hermesPath gateway install
        if ($LASTEXITCODE -ne 0) {
            throw "Hermes gateway install failed. Review the Hermes output above."
        }
        Write-Host "[INFO] Waiting for the elevated Hermes gateway installation to finish. No second install or restart will be started."
    }
    if (-not (Wait-HermesApi -TimeoutSeconds 120)) {
        if ($gatewayWasInstalled) {
            throw "Hermes gateway restarted, but its loopback API did not become healthy at 127.0.0.1:8642."
        }
        throw "Hermes gateway installation was started, but its loopback API did not become healthy within 120 seconds. Do not start another install; run 'hermes gateway status' and review the Scheduled Task result."
    }
    Write-Host "[PASS] Hermes loopback API is healthy."
} catch {
    if ($originalHermesEnvExists) {
        [IO.File]::WriteAllText($hermesEnvPath, $existingEnv, $utf8NoBom)
    } else {
        Remove-Item -LiteralPath $hermesEnvPath -Force -ErrorAction SilentlyContinue
    }
    Write-Warning "The original Hermes .env content was restored."
    throw
}

$powerShellPath = Join-Path $PSHOME "powershell.exe"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powerShellPath
$shortcut.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $residentTarget + '"'
$shortcut.WorkingDirectory = $installRoot
$shortcut.Description = "Local Assistant Resident Host v0.6.3"
$shortcut.Save()
Write-Host "[PASS] Per-user login shortcut installed: $shortcutPath"

Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
$launchArguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $residentTarget + '"'
Start-Process -FilePath $powerShellPath -ArgumentList $launchArguments -WindowStyle Hidden

Write-Host ""
Write-Host "Resident host installation complete."
Write-Host "Press Ctrl+Alt+Space, or double-click the $AssistantName tray icon."
Write-Host "The microphone is disabled and no command or response content is written to the host log."
Write-Host "Use this manager later: $managerTarget"
