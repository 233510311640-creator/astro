$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw "PowerShell 5 or newer is required."
}

$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python 3.12+ is required. Install it from python.org, then run this script again."
}

$version = & py -3.12 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 is not available through the Windows Python launcher."
}
& py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 or newer is required. Installed version: $version"
}

Write-Host "Using Python $version"
& py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e .

Write-Host ""
Write-Host "Setup complete. Start the assistant with:"
Write-Host ".\.venv\Scripts\python.exe -m local_assistant"
Write-Host ""
Write-Host "This milestone does not install a model, request admin access, or move files automatically."
