# One-time setup for Cypher's offline, streaming wake-word detector.
# It does not change Hermes, system Python packages, or browser settings.
$ErrorActionPreference = "Stop"
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$runtime = Join-Path $env:LOCALAPPDATA "Cypher\WakeRuntime"
$runtimePython = Join-Path $runtime "Scripts\python.exe"
$deps = Join-Path $runtime "Lib\site-packages"
$modelName = "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
$model = Join-Path $runtime $modelName
$archive = Join-Path $runtime "sherpa-kws-model.tar.bz2"
$expectedArchiveHash = "F170013B4716E41B62B9BFD809687C207CEF798EF9BC6534D524E17AF9B6561A"
$url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/$modelName.tar.bz2"
$worker = Join-Path (Split-Path -Parent $PSScriptRoot) "src\local_assistant\wake_worker.py"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python 3.12 is not installed at the expected local path. Install Cypher's existing voice prerequisites first."
}
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
    throw "The Cypher wake worker is missing. Run this script from the complete package."
}
if (-not (Test-Path -LiteralPath $runtimePython -PathType Leaf)) {
    & $python -m venv $runtime
    if ($LASTEXITCODE -ne 0) { throw "Could not create the isolated wake runtime." }
}
& $runtimePython -m pip install --disable-pip-version-check "numpy==2.2.6" "sherpa-onnx==1.13.8" "sounddevice==0.5.6" "sentencepiece==0.2.1" "pypinyin==0.55.0"
if ($LASTEXITCODE -ne 0) { throw "Could not install pinned local wake dependencies." }

if (-not (Test-Path -LiteralPath (Join-Path $model "tokens.txt") -PathType Leaf)) {
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
        Invoke-WebRequest -Uri $url -OutFile $archive -TimeoutSec 120
    }
    $hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    if ($hash -ne $expectedArchiveHash) {
        throw "The official wake-model archive did not match its pinned SHA-256. It was not extracted."
    }
    $paths = @(& tar -tf $archive)
    if ($LASTEXITCODE -ne 0 -or $paths.Count -eq 0) { throw "Could not inspect the wake-model archive." }
    foreach ($path in $paths) {
        if (-not $path.StartsWith("$modelName/") -or $path -match '(^/|^[A-Za-z]:|(^|/)\.\.(/|$))') {
            throw "The wake-model archive contains an unsafe path; it was not extracted."
        }
    }
    & tar -xf $archive -C $runtime
    if ($LASTEXITCODE -ne 0) { throw "Could not extract the verified wake-model archive." }
}

$check = & $python -I -B $worker --model-dir $model --deps-dir $deps --self-test 2>&1
if ($LASTEXITCODE -ne 0 -or @($check | Where-Object { $_ -eq "READY" }).Count -ne 1) {
    throw "The wake runtime did not initialize on this microphone. $check"
}
Write-Host "[PASS] Cypher's offline wake detector is ready. No speech was recorded during setup."
