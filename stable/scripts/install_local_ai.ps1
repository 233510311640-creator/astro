$ErrorActionPreference = "Stop"

Write-Host "This installs the free llama.cpp runtime through Windows Package Manager."
Write-Host "The model will run only on 127.0.0.1 and will not require an API key."
$answer = Read-Host "Type INSTALL to continue"
if ($answer -cne "INSTALL") {
    Write-Host "Cancelled."
    exit 0
}

winget install llama.cpp --accept-package-agreements --accept-source-agreements
if ($LASTEXITCODE -ne 0) {
    throw "llama.cpp installation failed."
}

Write-Host ""
Write-Host "llama.cpp installed. Run .\scripts\start_local_model.ps1 next."

