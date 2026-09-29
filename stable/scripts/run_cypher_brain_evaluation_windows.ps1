param(
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$endpoint = "http://127.0.0.1:11434"
$qwenCandidate = "qwen3.5:9b-q4_K_M"
$downloadConsent = "DOWNLOAD qwen3.5:9b-q4_K_M"
$benchmarkLauncher = Join-Path $PSScriptRoot "benchmark_cypher_models_windows.ps1"
$reportsRoot = Join-Path $projectRoot "reports"

Write-Host "Cypher v0.7 Brain Evaluation" -ForegroundColor Cyan
Write-Host "This preflight reads only Ollama's local model inventory and uses fixed test prompts."
Write-Host "It does not read personal files, change Hermes/Cypher settings, or request administrator access."
Write-Host ""

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama was not found in PATH. Start Ollama, reopen this folder, and try again."
}
if (-not (Test-Path -LiteralPath $benchmarkLauncher -PathType Leaf)) {
    throw "The benchmark launcher is missing. Extract the complete Cypher preflight package."
}

try {
    $null = Invoke-RestMethod -Method Get -Uri "$endpoint/api/version" -TimeoutSec 10
} catch {
    throw "Ollama's local API is not responding at $endpoint. Start Ollama and try again."
}

function Get-InstalledModelNames {
    $inventory = Invoke-RestMethod -Method Get -Uri "$endpoint/api/tags" -TimeoutSec 20
    return @($inventory.models | ForEach-Object { [string]$_.name })
}

$installed = @(Get-InstalledModelNames)
if ($installed -notcontains $qwenCandidate) {
    Write-Host "Recommended fast-model candidate is not installed: $qwenCandidate" -ForegroundColor Yellow
    Write-Host "It is a free local model and requires an approximately 6.6 GB download plus disk space."
    Write-Host "No download starts without the exact confirmation below. Press Enter to skip it."
    if (-not $SkipDownload) {
        $confirmation = Read-Host "Type $downloadConsent to continue"
        if ($confirmation -ceq $downloadConsent) {
            & ollama pull $qwenCandidate
            if ($LASTEXITCODE -ne 0) {
                throw "Ollama could not download $qwenCandidate. No Cypher settings were changed."
            }
            $installed = @(Get-InstalledModelNames)
        } else {
            Write-Host "Qwen download skipped. The evaluation will use installed candidates only."
        }
    } else {
        Write-Host "Qwen download skipped by -SkipDownload."
    }
}

$models = New-Object System.Collections.Generic.List[string]
foreach ($candidate in @($qwenCandidate, "gpt-oss:20b", "gemma4:e4b")) {
    if ($installed -contains $candidate) {
        $models.Add($candidate)
    }
}
if (($models -notcontains "gpt-oss:20b") -and
    ($installed -contains "local-assistant-brain-64k:latest")) {
    $models.Add("local-assistant-brain-64k:latest")
}
if ($models.Count -eq 0) {
    throw "None of Cypher's approved benchmark candidates are installed. No changes were made."
}

if (-not (Test-Path -LiteralPath $reportsRoot -PathType Container)) {
    $null = New-Item -ItemType Directory -Path $reportsRoot
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportPath = Join-Path $reportsRoot "cypher-brain-evaluation-$stamp.json"

Write-Host ""
Write-Host "Models selected:" -ForegroundColor Cyan
foreach ($modelName in $models) {
    Write-Host "  - $modelName"
}
Write-Host ""
Write-Host "Running 5 fixed safety/reasoning tasks per model. This can take several minutes."

& $benchmarkLauncher -Model $models.ToArray() -Context 16384 -Think off -Repetitions 1 -Output $reportPath
if ($LASTEXITCODE -ne 0) {
    throw "The Cypher benchmark stopped. No Hermes/Cypher settings were changed."
}

Write-Host ""
Write-Host "Evaluation complete." -ForegroundColor Green
Write-Host "Report: $reportPath"
Write-Host "Send this JSON report back for the v0.7 fast/deep model decision."
