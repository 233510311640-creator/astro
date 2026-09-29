param(
    [string[]]$Model,
    [ValidateRange(2048, 131072)]
    [int]$Context = 16384,
    [ValidateSet("off", "on", "low", "medium", "high")]
    [string]$Think = "off",
    [ValidateRange(1, 5)]
    [int]$Repetitions = 1,
    [string]$Output = "cypher-model-benchmark.json"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama was not found in PATH. Start Ollama, reopen PowerShell, and try again."
}

$version = & ollama --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Ollama is installed but did not respond: $version"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $projectRoot "src"
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot "local_assistant\model_benchmark.py"))) {
    throw "The Cypher benchmark source was not found under $sourceRoot. Extract the complete package and try again."
}

$python = $null
$pythonArgs = @()
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $python = $venvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pythonArgs = @("-3.12")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
} else {
    throw "Python 3.12 was not found. Re-run the Cypher setup before benchmarking."
}

$arguments = @(
    "-m", "local_assistant.model_benchmark",
    "--num-ctx", [string]$Context,
    "--think", $Think,
    "--repetitions", [string]$Repetitions,
    "--output", $Output
)
foreach ($modelName in $Model) {
    if (-not [string]::IsNullOrWhiteSpace($modelName)) {
        $arguments += @("--model", $modelName)
    }
}

Write-Host "Cypher Local Model Benchmark"
Write-Host "No personal files, conversations, credentials, or browser data are read."
Write-Host "The report contains fixed benchmark responses and performance metadata."
Write-Host ""

$previousPythonPath = $env:PYTHONPATH
try {
    if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
        $env:PYTHONPATH = $sourceRoot
    } else {
        $env:PYTHONPATH = "$sourceRoot;$previousPythonPath"
    }
    & $python @pythonArgs @arguments
    $benchmarkExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
if ($benchmarkExitCode -ne 0) {
    throw "The model benchmark process stopped with exit code $benchmarkExitCode."
}
