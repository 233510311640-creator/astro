$ErrorActionPreference = "Stop"

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    throw "Ollama was not found. Start or reinstall Ollama for Windows."
}

& ollama show "gpt-oss:20b" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "gpt-oss:20b is not installed."
}

$modelfile = Join-Path $env:TEMP "LocalAssistant.Modelfile"
@'
FROM gpt-oss:20b
PARAMETER num_ctx 16384
PARAMETER temperature 1
SYSTEM """
Reasoning: high
You are the private reasoning brain of a local Windows agent.
Plan carefully, use tools only when needed, and never claim an action succeeded without a tool result.
Never request or expose passwords, recovery keys, one-time codes, or banking credentials.
Destructive, external, financial, security, and bulk file actions require explicit user approval.
"""
'@ | Set-Content -Path $modelfile -Encoding UTF8

Write-Host "Creating a tuned 16K-context agent profile. This reuses the installed weights."
& ollama create "local-assistant-brain" -f $modelfile
if ($LASTEXITCODE -ne 0) {
    throw "The tuned agent profile could not be created."
}

Write-Host "Created local-assistant-brain. No model weights were duplicated."

