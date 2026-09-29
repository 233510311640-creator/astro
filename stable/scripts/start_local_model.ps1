$ErrorActionPreference = "Stop"

$model = "Qwen/Qwen3-8B-GGUF:Q4_K_M"
$common = @("-hf", $model, "--host", "127.0.0.1", "--port", "8080", "-ngl", "99", "-c", "16384")

$server = Get-Command llama-server -ErrorAction SilentlyContinue
if ($server) {
    Write-Host "Starting the local Qwen3 8B model. The first run downloads roughly 5 GB."
    & llama-server @common
    exit $LASTEXITCODE
}

$unified = Get-Command llama -ErrorAction SilentlyContinue
if ($unified) {
    Write-Host "Starting the local Qwen3 8B model. The first run downloads roughly 5 GB."
    & llama serve @common
    exit $LASTEXITCODE
}

throw "llama.cpp was not found. Run .\scripts\install_local_ai.ps1 first, then reopen PowerShell."

