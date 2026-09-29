$ErrorActionPreference = "Stop"

$model = "local-assistant-brain:latest"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    throw "Ollama was not found. Start or reinstall Ollama for Windows."
}

& ollama show $model *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The tuned agent brain was not found. Run .\scripts\configure_agent_brain.ps1 first."
}

$env:LOCAL_ASSISTANT_MODEL_URL = "http://127.0.0.1:11434"
$env:LOCAL_ASSISTANT_MODEL = $model
& .\.venv\Scripts\python.exe -m local_assistant

