param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("status", "start", "stop", "uninstall")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "LocalAssistantHost"
$residentPath = Join-Path $installRoot "resident_assistant_windows.ps1"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$stopRequestPath = Join-Path $installRoot "stop.request"
$hermesEnvPath = Join-Path $env:LOCALAPPDATA "hermes\.env"
$startupRoot = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupRoot "Local Assistant Host.lnk"
$managedBegin = "# BEGIN LOCAL_ASSISTANT_HOST_V0_6"
$managedEnd = "# END LOCAL_ASSISTANT_HOST_V0_6"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-ResidentState {
    if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) {
        return "stopped"
    }
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]$heartbeat.timestamp
        if ($age.TotalSeconds -ge -5 -and $age.TotalSeconds -le 15) {
            return [string]$heartbeat.status
        }
    } catch {
    }
    return "stopped"
}

function Stop-ResidentHost {
    if (-not (Test-Path -LiteralPath $installRoot -PathType Container)) {
        return
    }
    [IO.File]::WriteAllText($stopRequestPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
    $deadline = [DateTime]::UtcNow.AddSeconds(12)
    do {
        if ((Get-ResidentState) -eq "stopped") {
            Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
            return
        }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "The resident host did not stop within 12 seconds. Exit it from the tray icon and retry."
}

switch ($Action) {
    "status" {
        Write-Host "Resident host: $(Get-ResidentState)"
        Write-Host "Installed: $([bool](Test-Path -LiteralPath $residentPath -PathType Leaf))"
        Write-Host "Starts at sign-in: $([bool](Test-Path -LiteralPath $shortcutPath -PathType Leaf))"
        Write-Host "Hermes endpoint: http://127.0.0.1:8642"
        Write-Host "Activation: Ctrl+Alt+Space"
        Write-Host "Microphone: disabled"
        Write-Host "Host content logging: disabled"
    }
    "start" {
        if (-not (Test-Path -LiteralPath $residentPath -PathType Leaf)) {
            throw "Resident host is not installed."
        }
        Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
        $powerShellPath = Join-Path $PSHOME "powershell.exe"
        $launchArguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $residentPath + '"'
        Start-Process -FilePath $powerShellPath -ArgumentList $launchArguments -WindowStyle Hidden
        Write-Host "Start requested. Look for the tray icon or press Ctrl+Alt+Space."
    }
    "stop" {
        Stop-ResidentHost
        Write-Host "Resident host stopped. It will start again at the next Windows sign-in."
    }
    "uninstall" {
        Write-Host "This removes the resident tray host, its login shortcut, local token, and its managed Hermes API settings."
        Write-Host "It does not delete Hermes, Ollama, the capability broker, conversations, or personal files."
        $confirmation = Read-Host "Type REMOVE RESIDENT HOST to continue"
        if ($confirmation -cne "REMOVE RESIDENT HOST") {
            Write-Host "Cancelled."
            exit 0
        }

        Stop-ResidentHost
        Remove-Item -LiteralPath $shortcutPath -Force -ErrorAction SilentlyContinue

        if (Test-Path -LiteralPath $hermesEnvPath -PathType Leaf) {
            $existing = Get-Content -LiteralPath $hermesEnvPath -Raw
            $pattern = "(?ms)^" + [regex]::Escape($managedBegin) + "\r?\n.*?^" + [regex]::Escape($managedEnd) + "\r?\n?"
            $updated = [regex]::Replace($existing, $pattern, "").TrimEnd()
            if (-not [string]::IsNullOrEmpty($updated)) {
                $updated += [Environment]::NewLine
            }
            [IO.File]::WriteAllText($hermesEnvPath, $updated, $utf8NoBom)
        }

        $hermesCommand = Get-Command "hermes.exe" -ErrorAction SilentlyContinue
        if ($hermesCommand) {
            & $hermesCommand.Source gateway restart
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Hermes gateway could not be restarted. Restart it manually so the API setting removal takes effect."
            }
        } else {
            Write-Warning "Hermes CLI was not found. Restart the Hermes gateway manually so the API setting removal takes effect."
        }

        $expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "LocalAssistantHost"))
        if ([IO.Path]::GetFullPath($installRoot) -ne $expectedRoot) {
            throw "Refusing to remove an unexpected install path."
        }
        Remove-Item -LiteralPath $installRoot -Recurse -Force
        Write-Host "Resident host removed."
        Write-Host "Hermes gateway registration was preserved in case other Hermes features use it."
    }
}
