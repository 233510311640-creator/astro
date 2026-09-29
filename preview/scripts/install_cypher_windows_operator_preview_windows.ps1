$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$sandboxRoot = Join-Path $env:USERPROFILE "Desktop\Hermes Sandbox"

Write-Host "Cypher v0.8.2 Windows Operator Preview 2"
Write-Host "This installs the tested broker update, seeds built-in app launch entries,"
Write-Host "updates the resident Core manager, and preserves existing permissions and data."
Write-Host "It does not edit Hermes registration; the exact replacement command is generated for review."
Write-Host ""

& (Join-Path $PSScriptRoot "setup_capability_broker_windows.ps1") -SandboxRoot $sandboxRoot
if ($LASTEXITCODE -ne 0) {
    throw "The Windows operator broker setup failed. The resident Core was not changed."
}

& (Join-Path $PSScriptRoot "install_cypher_core_preview_windows.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "The resident Core update failed. Review the error above."
}

Write-Host ""
Write-Host "[PASS] Cypher Windows Operator Preview files are installed."
Write-Host "Next: replace the hermes-sandbox registration using REGISTER_COMMAND.txt, then run"
Write-Host "CONFIGURE_CYPHER_HERMES_TOOLS.cmd to test the resulting 28-tool connection."
