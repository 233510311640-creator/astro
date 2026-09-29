param(
    [string]$SandboxRoot = "$env:USERPROFILE\Desktop\Hermes Sandbox"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "src"

Write-Host "Cypher Windows Operator Preview v0.8.2-alpha1"
Write-Host "This setup does not approve real folders, enable Hermes built-in tools, edit Hermes config, or move files."
Write-Host "Real-folder capabilities remain disabled until a person adds an exact root and explicit scopes."
Write-Host "Built-in Windows apps are registered for argument-free launch; arbitrary commands remain unavailable."

$version = & py -3.12 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 is required. The Windows Python launcher could not find it."
}
Write-Host "[PASS] $version"

if (-not (Test-Path -LiteralPath $SandboxRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $SandboxRoot -Force | Out-Null
    Write-Host "[PASS] Created sandbox: $SandboxRoot"
} else {
    Write-Host "[PASS] Sandbox exists: $SandboxRoot"
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $sourceRoot
    & py -3.12 -m unittest discover -s (Join-Path $projectRoot "tests") -v
    if ($LASTEXITCODE -ne 0) {
        throw "Broker tests failed. Do not connect it to Hermes."
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$localData = [Environment]::GetFolderPath("LocalApplicationData")
$windowsAppsPath = Join-Path $localData "LocalAssistantBroker\windows_apps.json"
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $sourceRoot
    & py -3.12 -m local_assistant.windows_admin --config $windowsAppsPath seed-builtins
    if ($LASTEXITCODE -ne 0) {
        throw "Built-in Windows app registration failed. Do not connect this broker to Hermes."
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $sourceRoot
    & py -3.12 -m local_assistant.operator_preflight
    if ($LASTEXITCODE -ne 0) {
        throw "Windows DPAPI preflight failed. Do not connect this broker to Hermes."
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$launcher = Join-Path $projectRoot "scripts\start_capability_broker_windows.ps1"
$commandFile = Join-Path $projectRoot "REGISTER_COMMAND.txt"
$registration = @"
hermes mcp add hermes-sandbox --command powershell.exe --args -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$launcher" -Root "$SandboxRoot"
"@
Set-Content -LiteralPath $commandFile -Value $registration -Encoding UTF8

Write-Host ""
Write-Host "[PASS] All local broker tests passed."
Write-Host "[PASS] Built-in Windows app allowlist is ready."
Write-Host "[INFO] Registration command saved to: $commandFile"
Write-Host "[INFO] No Hermes configuration was changed."
