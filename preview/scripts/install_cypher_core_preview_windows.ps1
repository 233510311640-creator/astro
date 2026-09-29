param(
    [ValidatePattern("^[A-Za-z0-9 _-]{1,32}$")]
    [string]$AssistantName = "Cypher",
    [switch]$ValidationOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $projectRoot "windows\Cypher.CorePreview\CypherCoreHost.cs"
$workflowSources = @(
    (Join-Path $projectRoot "windows\Cypher.CorePreview\WindowsWorkflow.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\WindowsWorkflowNative.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\WindowsWorkflowHost.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\WindowsWorkflowSelfTest.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\ResearchHost.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\FileTaskClient.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\FileTaskHost.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\RuntimeHost.cs"),
    (Join-Path $projectRoot "windows\Cypher.CorePreview\DocumentHost.cs")
    (Join-Path $projectRoot "windows\Cypher.CorePreview\VoiceHost.cs")
    (Join-Path $projectRoot "windows\Cypher.CorePreview\CloudVoiceHost.cs")
    (Join-Path $projectRoot "windows\Cypher.CorePreview\VoiceCapture.cs")
    (Join-Path $projectRoot "windows\Cypher.CorePreview\VoiceActivityGate.cs")
    (Join-Path $projectRoot "windows\Cypher.CorePreview\WakeHost.cs")
)
$documentWorkerSource = Join-Path $projectRoot "windows\Cypher.CorePreview\document_worker.pyz"
$pdfParserSource = Join-Path $projectRoot "windows\Cypher.CorePreview\pdf_parser.pyz"
$officeParserSource = Join-Path $projectRoot "windows\Cypher.CorePreview\office_parser.pyz"
$heroArtworkSource = Join-Path $projectRoot "windows\Cypher.CorePreview\assets\cypher-signal-core.png"
$runtimeWorkerSource = Join-Path $projectRoot "src\local_assistant\runtime_worker.py"
$fileWorkerSource = Join-Path $projectRoot "windows\Cypher.CorePreview\file_operator.pyz"
$fileHostSource = Join-Path $projectRoot "windows\Cypher.CorePreview\FileTaskClient.cs"
$researchWorkerSource = Join-Path $projectRoot "src\local_assistant\research_worker.py"
$voiceWorkerSource = Join-Path $projectRoot "src\local_assistant\voice_worker.py"
$wakeWorkerSource = Join-Path $projectRoot "src\local_assistant\wake_worker.py"
$wakeRuntimeRoot = Join-Path $env:LOCALAPPDATA "Cypher\WakeRuntime"
$wakeDepsPath = Join-Path $wakeRuntimeRoot "Lib\site-packages"
$wakeModelPath = Join-Path $wakeRuntimeRoot "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"
$researchHostSource = Join-Path $projectRoot "windows\Cypher.CorePreview\ResearchHost.cs"
$managerSource = Join-Path $PSScriptRoot "manage_cypher_core_preview_windows.ps1"
$installRoot = Join-Path $env:LOCALAPPDATA "Cypher\CorePreview"
$rollbackRoot = Join-Path $installRoot "rollback"
$installedExe = Join-Path $installRoot "CypherCoreHost.exe"
$installedManager = Join-Path $installRoot "manage_cypher_core_preview_windows.ps1"
$installedSource = Join-Path $installRoot "CypherCoreHost.cs"
$installedHeroArtwork = Join-Path $installRoot "cypher-signal-core.png"
$configPath = Join-Path $installRoot "host_config.json"
$tokenPath = Join-Path $installRoot "api_key.bin"
$heartbeatPath = Join-Path $installRoot "heartbeat.json"
$stopRequestPath = Join-Path $installRoot "stop.request"
$checkpointPath = Join-Path $installRoot "active-task.json"
$failureReceiptPath = Join-Path $installRoot "last-failure.json"
$legacyRoot = Join-Path $env:LOCALAPPDATA "LocalAssistantHost"
$legacyTokenPath = Join-Path $legacyRoot "api_key.dpapi"
$legacyHeartbeatPath = Join-Path $legacyRoot "heartbeat.json"
$legacyStopPath = Join-Path $legacyRoot "stop.request"
$legacyResidentPath = Join-Path $legacyRoot "resident_assistant_windows.ps1"
$startupRoot = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupRoot "Local Assistant Host.lnk"
$shortcutBackup = Join-Path $rollbackRoot "Local Assistant Host.v063.lnk"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Security

function Resolve-CypherPython312 {
    $candidates = New-Object System.Collections.Generic.List[string]
    $launcher = Get-Command "py.exe" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($launcher -and [IO.Path]::IsPathRooted([string]$launcher.Source)) {
        $launcherResult = [string](& ([string]$launcher.Source) -3.12 -I -S -c "import sys; print(sys.executable)" 2>$null)
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($launcherResult)) {
            $candidates.Add($launcherResult.Trim())
        }
    }

    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Python312\python.exe")
    )) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate)) {
            $candidates.Add([string]$candidate)
        }
    }

    $pythonCommand = Get-Command "python.exe" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pythonCommand -and [IO.Path]::IsPathRooted([string]$pythonCommand.Source)) {
        $candidates.Add([string]$pythonCommand.Source)
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not [IO.Path]::IsPathRooted($candidate) -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        $fullPath = [IO.Path]::GetFullPath($candidate)
        $item = Get-Item -LiteralPath $fullPath
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            continue
        }
        $version = [string](& $fullPath -I -S -c "import sys; print(sys.version_info[0], sys.version_info[1], sep='.')" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $version.Trim() -eq "3.12") {
            return $fullPath
        }
    }
    throw "The existing Python 3.12 interpreter could not be resolved. No installation changes were made."
}

Write-Host "Cypher v0.10.21.0 Hands-Free Voice Preview"
Write-Host "After sign-in, say Hello Cypher or Cypher. Wake listening stays local. Voice output now reports start, completion, or Windows playback failure without logging speech content. Existing action approvals remain."
Write-Host "ASK IMAGE in the left rail fills the explicit approved-PNG command. Use Files: folders to find your folder name. The installed Qwen 3.5 9B model is the vision default; responses remain unverified interpretations."
Write-Host "Vision: describe ROOT `"image.png`" or Vision: ask ROOT `"image.png`" : QUESTION interprets one explicitly named approved PNG through one installed local vision-model call. No attachment, camera, screenshot, web or Windows action; output is not verified OCR."
Write-Host "Docs: answer-all ROOT : QUESTION scans the same bounded approved TXT/PDF/Office scope as search-all, selects anonymous question-relevant excerpts from at most four files, and makes at most one verified local-model call. It prints checked cited sentences and exact source files, hashes, locations and quotes. No index, file change or public request."
Write-Host "Remind: YYYY-MM-DD HH:MM : message saves an explicit local-time reminder, protected with Windows-user DPAPI. Remind: list and Remind: cancel ID manage pending reminders. Cypher notifies through its resident tray when running; overdue reminders notify when it next starts. Reminder text is not sent to Hermes or a web service."
Write-Host "Docs: search-all ROOT : query scans current extractable text across bounded TXT, PDF, DOCX, PPTX and XLSX files in one approved folder. It has no model call, saved index, network request, macro/formula execution or file change."
Write-Host "Ctrl+Alt+Space starts voice; Ctrl+Win+Alt opens the chat. The tray also opens the command center."
Write-Host "Natural browser open and search requests route locally before the model. Brave, Edge, Chrome, and Firefox are discovered only from fixed standard install paths. A reviewed search query becomes one fixed DuckDuckGo HTTPS URL; the exact executable, query, and destination are bound to one native approval and passed without a shell. Other applications still require registration."
Write-Host "Web: read PUBLIC-HTTPS-URL uses a separate isolated reader to return at most four exact excerpts. It has no browser profile, cookies, login state, scripts, model call, file tools or Windows actions. Page text is untrusted and cannot authorize an action."
Write-Host "Web: ask PUBLIC-HTTPS-URL : QUESTION uses the same isolated one-page reader, supplies only bounded passages to at most one verified installed local-model call, and displays checked findings with exact supporting text. It has no browser profile, cookies, login state, scripts, file tools or Windows actions."
Write-Host "Web: links PUBLIC-HTTPS-URL maps at most six visible eligible same-site HTTPS destinations without opening them, using a model, running scripts, submitting forms, clicking, or downloading. A listed destination is opened only through a separately submitted exact Open command and the existing one-time browser approval."
Write-Host "Web: follow PUBLIC-HTTPS-URL : NUMBER rebuilds the current safe map, reads only the selected same-host destination, and shows exact bounded excerpts. It has no model, browser profile, cookies, scripts, forms, or file and Windows actions."
Write-Host "Web: forms PUBLIC-HTTPS-URL inspects visible same-host HTML form metadata only. It never displays current or hidden field values, fills controls, submits forms, or calls a model or local action."
Write-Host "Web: search PUBLIC-HTTPS-URL : QUERY sends the typed query through exactly one eligible same-host GET search form, then previews exact result-page excerpts. It rejects POST, hidden-field and ambiguous forms; the query may reach that site."
Write-Host "Other applications must already be in the human-managed registry. Non-HTTPS, IP-literal, local, credentialed, whitespace or multi-destination requests reject. Search uses only DuckDuckGo and discloses the reviewed query. This is bounded URL delivery, not result reading or interactive browser automation."
Write-Host "Docs: search performs a bounded plain-text scan with no model or saved index. Docs: search-all adds PDF and Office text within a 40-file / 16 MiB / 45-second scan cap. Ask/answer/summarize accept one explicitly selected UTF-8 text file up to 1 MiB, PDF up to 8 MiB / 100 pages, or DOCX/PPTX/XLSX up to 8 MiB. Compare accepts two to four supported files. PDF and Office bytes go to separate pinned parser children with no path, model, network or action context. No OCR, macro/formula execution, public request or file change."
Write-Host "System status reads local Ollama metadata without generation. Runtime: benchmark makes one explicit synthetic generation on the selected installed local model; no retry, download, unload or substitution."
Write-Host "Files: list/find/read browse granted folders without a model call. File changes prepare exact local file plans, use the native approval panel, verify changes and offer undo. No model call. Folder permissions are granted only after a folder selection and review."
Write-Host "The new offline file self-test checks Windows DPAPI, organize, undo and Stop rollback in a temporary fixture before replacing Cypher."
Write-Host "This installs a compiled, streaming resident host beside the verified v0.6.3 rollback baseline."
Write-Host "It does not change Hermes tools, broker permissions, inventory roots, model files, or microphone access."
Write-Host "It adds metadata-only task checkpoints and authoritative restart reconciliation; prompts and answers remain memory-only."
Write-Host "It also adds deterministic read-only Windows observation for registered apps and titled top-level windows without model inference."
Write-Host "One exact registered-app launch, visible-window focus, or supported UI Automation action requires a fresh native approval and local postcondition check."
Write-Host "Packaged apps may be matched by an exact registered AppUserModelID. Bounded text entry must be enabled separately for each app."
Write-Host "A natural 'Open registered-app and write: text' request now resolves the app and one safe editor without copied window/control IDs."
Write-Host "That workflow remains a single action behind one fresh native approval; ambiguous apps or editors fail closed."
Write-Host "Ordered workflows support up to six steps across three registered apps: open, replace editor text, focus, minimize, and restore."
Write-Host "The full plan has one native approval. Each step is revalidated and checkpointed; Stop prevents later steps and restart never replays an action."
Write-Host "There is no arming countdown. Stop cancels pending observation waits; ambiguity reports include bounded window metadata."
Write-Host "This release recognizes only a previously proved frame/content pair during hosted-app transitions. Unknown extra windows still reject."
Write-Host "Research: with no URL lines makes one official English Wikipedia API request using only the typed question and keeps up to three candidates in provider relevance order."
Write-Host "Cypher reads discovered candidates only until two usable sources are available. Oversized readable pages contribute only a bounded 1 MiB prefix."
Write-Host "Adding one to five public HTTPS URL lines keeps the explicit-source route and keeps the question local. Search titles are not evidence."
Write-Host "Research papers: makes one keyless official OpenAlex Works request. Unambiguous relationship questions use the two normalized literal concept phrases joined by fixed Boolean AND. Other questions retain the punctuation-safe query; reserved ? and * wildcard characters never become provider syntax."
Write-Host "The original question remains local for synthesis. Only an exact OpenAlex HTTP 503 permits one immediate keyless Crossref Works request with the same provider-neutral search terms, without OpenAlex Boolean syntax. Cypher keeps the original question local for source ranking on either provider route."
Write-Host "The route keeps up to eight provider-ranked records and supplies at most two checked English abstracts to one local-model call. Crossref deposited abstracts are normalized before evidence selection."
Write-Host "Cypher now validates up to eight returned abstracts and selects the strongest at most two using bounded local question-term coverage of abstract text; provider order only breaks exact local-score ties."
Write-Host "For explicit relationship questions, a deterministic post-check requires both extracted concepts and relationship wording in one cited passage. Indirect chains are withheld, with no extra provider request or model call."
Write-Host "Before synthesis, recognized academic relationship questions screen the existing bounded passages. If none pass the lexical check, no local model request runs. Draft rejection is reported separately from this passage-level evidence gap."
Write-Host "All returned IPv4 addresses are validated. Cypher may try up to four only while establishing TLS before each permitted HTTP request; neither provider request is retried or delayed."
Write-Host "Titles, identifiers, provider ranking, scores, citation counts, and other metadata are not evidence or model input. Neither request sends an API key, authorization header, or billing credential."
Write-Host "Research has no action tools, cookies, logins, scripts, payment, retry loop, extra approval, warning, or arming countdown. Stop remains available while the owned worker runs; no model download is needed."
Write-Host "Text is not read back, saved, or undone. The prior title-stability and packaged-app identity fixes are retained."
Write-Host "Password fields, existing Value/Document text reads, raw input, clipboard automation, and screenshots stay unavailable."
Write-Host "The host runs as the signed-in standard user. Chat uses Hermes on loopback."
Write-Host "If Ollama is not already reachable, the compiled host starts only the installer-pinned local ollama.exe with the fixed serve argument and verifies its loopback version endpoint."
Write-Host ""

if ($env:OS -ne "Windows_NT") {
    throw "This installer is only for native Windows."
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from a normal, non-administrator PowerShell window. Cypher Core must not be installed elevated."
}
$ollamaCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe")
)
$ollamaCommand = Get-Command "ollama.exe" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ollamaCommand -and [IO.Path]::IsPathRooted([string]$ollamaCommand.Source)) {
    $ollamaCandidates += [string]$ollamaCommand.Source
}
$ollamaPath = $ollamaCandidates |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_ -PathType Leaf) } |
    ForEach-Object { [IO.Path]::GetFullPath($_) } |
    Select-Object -Unique -First 1
if (-not $ollamaPath) {
    throw "Ollama is not installed for this Windows user. No Cypher installation changes were made."
}
$ollamaItem = Get-Item -LiteralPath $ollamaPath
if (($ollamaItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "The resolved Ollama executable is a reparse point. No Cypher installation changes were made."
}
$ollamaHash = (Get-FileHash -LiteralPath $ollamaPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ollamaHash -notmatch '^[a-f0-9]{64}$') {
    throw "The resolved Ollama executable could not be pinned. No Cypher installation changes were made."
}
Write-Host "[PASS] Local Ollama executable resolved and SHA-256 pinned for bounded startup."
foreach ($required in (@($sourcePath, $managerSource) + $workflowSources)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "The package is incomplete. Extract the whole ZIP into one folder before installing."
    }
}
if (-not (Test-Path -LiteralPath $researchWorkerSource -PathType Leaf)) {
    throw "The research worker is missing. Extract the complete package; nothing was installed."
}
if (-not (Test-Path -LiteralPath $voiceWorkerSource -PathType Leaf)) { throw "The offline voice worker is missing." }
if (-not (Test-Path -LiteralPath $wakeWorkerSource -PathType Leaf)) { throw "The offline wake worker is missing." }
$wakeWorkerHash = (Get-FileHash -LiteralPath $wakeWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$wakeExpectedHash = [regex]::Match((Get-Content -LiteralPath (Join-Path $projectRoot "windows\Cypher.CorePreview\WakeHost.cs") -Raw), 'WakeWorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($wakeWorkerHash.Length -ne 64 -or $wakeWorkerHash -ne $wakeExpectedHash) { throw "The wake worker failed its integrity check." }
if (-not (Test-Path -LiteralPath (Join-Path $wakeDepsPath "sherpa_onnx\__init__.py") -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $wakeModelPath "tokens.txt") -PathType Leaf)) {
    throw "The offline wake runtime is missing. Run scripts/setup_cypher_wake_runtime_windows.ps1 first. No installed files were changed."
}
$voiceWorkerHash = (Get-FileHash -LiteralPath $voiceWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$voiceExpectedHash = [regex]::Match((Get-Content -LiteralPath (Join-Path $projectRoot "windows\Cypher.CorePreview\VoiceHost.cs") -Raw), 'VoiceWorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($voiceWorkerHash -ne $voiceExpectedHash) { throw "The voice worker failed its integrity check." }
if (-not (Test-Path -LiteralPath $fileWorkerSource -PathType Leaf)) { throw "The desktop file worker is missing." }
if (-not (Test-Path -LiteralPath $documentWorkerSource -PathType Leaf)) { throw "The document worker is missing." }
if (-not (Test-Path -LiteralPath $pdfParserSource -PathType Leaf)) { throw "The PDF parser is missing." }
if (-not (Test-Path -LiteralPath $officeParserSource -PathType Leaf)) { throw "The Office parser is missing." }
if (-not (Test-Path -LiteralPath $heroArtworkSource -PathType Leaf)) { throw "The Cypher signal artwork is missing." }
$heroArtworkHash = (Get-FileHash -LiteralPath $heroArtworkSource -Algorithm SHA256).Hash.ToLowerInvariant()
$heroExpectedHash = [regex]::Match((Get-Content -LiteralPath $sourcePath -Raw), 'HeroArtworkSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($heroExpectedHash.Length -ne 64 -or $heroArtworkHash -ne $heroExpectedHash) { throw "The Cypher signal artwork failed its integrity check." }
$documentWorkerHash = (Get-FileHash -LiteralPath $documentWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$documentExpectedHash = [regex]::Match((Get-Content -LiteralPath $fileHostSource -Raw), 'DocumentWorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($documentExpectedHash.Length -ne 64 -or $documentWorkerHash -ne $documentExpectedHash) { throw "The document worker failed its integrity check." }
$pdfParserHash = (Get-FileHash -LiteralPath $pdfParserSource -Algorithm SHA256).Hash.ToLowerInvariant()
$pdfParserExpectedHash = [regex]::Match((Get-Content -LiteralPath $fileHostSource -Raw), 'PdfParserSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($pdfParserExpectedHash.Length -ne 64 -or $pdfParserHash -ne $pdfParserExpectedHash) { throw "The PDF parser failed its integrity check." }
$officeParserHash = (Get-FileHash -LiteralPath $officeParserSource -Algorithm SHA256).Hash.ToLowerInvariant()
$officeParserExpectedHash = [regex]::Match((Get-Content -LiteralPath $fileHostSource -Raw), 'OfficeParserSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($officeParserExpectedHash.Length -ne 64 -or $officeParserHash -ne $officeParserExpectedHash) { throw "The Office parser failed its integrity check." }
if (-not (Test-Path -LiteralPath $runtimeWorkerSource -PathType Leaf)) { throw "The runtime worker is missing." }
$runtimeWorkerHash = (Get-FileHash -LiteralPath $runtimeWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$runtimeExpectedHash = [regex]::Match((Get-Content -LiteralPath $fileHostSource -Raw), 'RuntimeWorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($runtimeExpectedHash.Length -ne 64 -or $runtimeWorkerHash -ne $runtimeExpectedHash) { throw "The runtime worker failed its integrity check." }
$fileWorkerHash = (Get-FileHash -LiteralPath $fileWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$fileExpectedHash = [regex]::Match((Get-Content -LiteralPath $fileHostSource -Raw), 'WorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($fileExpectedHash.Length -ne 64 -or $fileWorkerHash -ne $fileExpectedHash) { throw "The desktop file worker failed its integrity check." }
$researchWorkerHash = (Get-FileHash -LiteralPath $researchWorkerSource -Algorithm SHA256).Hash.ToLowerInvariant()
$researchExpectedHash = [regex]::Match((Get-Content -LiteralPath $researchHostSource -Raw), 'WorkerSha256 = "([a-f0-9]{64})";').Groups[1].Value
if ($researchWorkerHash -ne $researchExpectedHash) {
    throw "The research worker does not match the compiled-host source. No installation changes were made."
}
$researchPythonPath = Resolve-CypherPython312
$voiceModelRoot = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--Systran--faster-whisper-base\snapshots"
$voiceModelPath = Get-ChildItem -LiteralPath $voiceModelRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { (Test-Path -LiteralPath (Join-Path $_.FullName "model.bin") -PathType Leaf) -and (Test-Path -LiteralPath (Join-Path $_.FullName "tokenizer.json") -PathType Leaf) } |
    Select-Object -ExpandProperty FullName -First 1
if (-not $voiceModelPath) { throw "The local faster-whisper base model is missing. No installation changes were made." }
& $researchPythonPath -I -B -c "import faster_whisper, numpy, scipy; print('offline voice dependencies available')"
if ($LASTEXITCODE -ne 0) { throw "Offline voice dependencies are not installed in the configured Python. No installation changes were made." }
$managerTokens = $null
$managerErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($managerSource, [ref]$managerTokens, [ref]$managerErrors)
if ($managerErrors.Count -gt 0) {
    throw "The packaged manager failed its PowerShell parser check. No installation changes were made."
}
if (-not (Test-Path -LiteralPath $legacyTokenPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $legacyResidentPath -PathType Leaf)) {
    throw "The verified v0.6.3 resident host was not found. Keep it installed so this preview has a safe rollback path."
}

$release = Get-ItemPropertyValue -LiteralPath "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" -Name Release -ErrorAction SilentlyContinue
if (-not $release -or [int64]$release -lt 528040) {
    throw ".NET Framework 4.8 or later is required. Windows 11 normally includes it."
}
Write-Host "[PASS] .NET Framework 4.8 or later is available."

$cscCandidates = @(
    (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe")
)
$cscPath = $cscCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $cscPath) {
    throw "The Windows .NET compiler was not found. No installation changes were made."
}

$frameworkRoot = Split-Path -Parent $cscPath
$frameworkWpfRoot = Join-Path $frameworkRoot "WPF"

function Resolve-FrameworkAssembly {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $candidates = @(
        (Join-Path $frameworkWpfRoot $Name),
        (Join-Path $frameworkRoot $Name)
    )
    $programRoots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
        Select-Object -Unique
    foreach ($programRoot in $programRoots) {
        $referenceRoot = Join-Path $programRoot "Reference Assemblies\Microsoft\Framework\.NETFramework"
        foreach ($version in @("v4.8.1", "v4.8", "v4.7.2")) {
            $candidates += Join-Path (Join-Path $referenceRoot $version) $Name
        }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }
    throw "Required .NET Framework assembly '$Name' was not found beside the Windows compiler or in the installed reference assemblies. No installation changes were made."
}

$windowsBasePath = Resolve-FrameworkAssembly "WindowsBase.dll"
$presentationCorePath = Resolve-FrameworkAssembly "PresentationCore.dll"
$presentationFrameworkPath = Resolve-FrameworkAssembly "PresentationFramework.dll"
$systemXamlPath = Resolve-FrameworkAssembly "System.Xaml.dll"
$uiAutomationClientPath = Resolve-FrameworkAssembly "UIAutomationClient.dll"
$uiAutomationTypesPath = Resolve-FrameworkAssembly "UIAutomationTypes.dll"
$speechAssemblyPath = Join-Path $env:WINDIR "Microsoft.NET\assembly\GAC_MSIL\System.Speech\v4.0_4.0.0.0__31bf3856ad364e35\System.Speech.dll"
if (-not (Test-Path -LiteralPath $speechAssemblyPath -PathType Leaf)) {
    throw "The .NET Framework 4 System.Speech assembly was not found. No installation changes were made."
}
foreach ($assemblyPath in @($windowsBasePath, $presentationCorePath, $presentationFrameworkPath, $systemXamlPath, $uiAutomationClientPath, $uiAutomationTypesPath, $speechAssemblyPath)) {
    Write-Host "[PASS] Framework assembly: $assemblyPath"
}

$pythonVersion = & $researchPythonPath --version 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 is required for the pre-install safety tests."
}
Write-Host "[PASS] $pythonVersion"
$wakeCheck = & $researchPythonPath -I -B $wakeWorkerSource --model-dir $wakeModelPath --deps-dir $wakeDepsPath --self-test 2>&1
if ($LASTEXITCODE -ne 0 -or @($wakeCheck | Where-Object { $_ -eq "READY" }).Count -ne 1) {
    throw "The offline wake model did not pass its self-test. No installed files were changed."
}
Write-Host "[PASS] Offline wake model initialized; microphone format is supported. No audio was recorded."

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    foreach ($testPattern in @(
        "test_cypher_core.py",
        "test_cypher_core_windows.py",
        "test_approved_actions.py",
        "test_capability_broker.py",
        "test_inventory_broker.py",
        "test_organization_planner.py",
        "test_task_lifecycle.py",
        "test_model_benchmark.py",
        "test_model_workflow.py",
        "test_permissioned_operator.py",
        "test_file_tasks.py",
        "test_file_browser.py",
        "test_document_worker.py",
        "test_file_worker_package.py",
        "test_runtime_worker.py",
        "test_windows_operator.py",
        "test_research_worker.py"
        "test_voice_worker.py"
        "test_wake_worker.py"
    )) {
        & $researchPythonPath -m unittest discover -s (Join-Path $projectRoot "tests") -p $testPattern -v
        if ($LASTEXITCODE -ne 0) {
            throw "Required safety test failed: $testPattern. No resident-host change was made."
        }
    }
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

$buildRoot = Join-Path ([IO.Path]::GetTempPath()) ("cypher-core-build-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $buildRoot | Out-Null
$builtExe = Join-Path $buildRoot "CypherCoreHost.exe"
try {
    $compilerArguments = @(
        "/nologo",
        "/target:winexe",
        "/optimize+",
        "/platform:anycpu",
        "/codepage:65001",
        "/out:$builtExe",
        "/reference:System.dll",
        "/reference:System.Core.dll",
        "/reference:System.Net.Http.dll",
        "/reference:System.Web.Extensions.dll",
        "/reference:System.Security.dll",
        "/reference:$windowsBasePath",
        "/reference:$presentationCorePath",
        "/reference:$presentationFrameworkPath",
        "/reference:$systemXamlPath",
        "/reference:$uiAutomationClientPath",
        "/reference:$uiAutomationTypesPath",
        "/reference:System.Windows.Forms.dll",
        "/reference:System.Drawing.dll",
        "/reference:$speechAssemblyPath",
        $sourcePath
    )
    $compilerArguments += $workflowSources
    & $cscPath $compilerArguments
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $builtExe -PathType Leaf)) {
        throw "The compiled Cypher host did not build successfully. No resident-host change was made."
    }
    Copy-Item -LiteralPath $heroArtworkSource -Destination (Join-Path $buildRoot "cypher-signal-core.png") -Force
    $selfTest = Start-Process -FilePath $builtExe -ArgumentList "--self-test" -Wait -PassThru
    if ($selfTest.ExitCode -ne 0) {
        throw "The compiled Cypher host failed its self-test with code $($selfTest.ExitCode). No resident-host change was made."
    }
    Write-Host "[PASS] Compiled host built and passed its self-test."

    Copy-Item -LiteralPath $researchWorkerSource -Destination (Join-Path $buildRoot "research_worker.py") -Force
    & $researchPythonPath -I -B $voiceWorkerSource --self-test
    if ($LASTEXITCODE -ne 0) { throw "The local voice worker failed its offline self-test. No resident-host change was made." }
    $researchSelfTest = Start-Process -FilePath $builtExe -ArgumentList ('--research-self-test "' + $researchPythonPath + '"') -Wait -PassThru
    if ($researchSelfTest.ExitCode -ne 0) {
        throw "The owned research worker failed its offline self-test with code $($researchSelfTest.ExitCode). No resident-host change was made."
    }
    Write-Host "[PASS] Owned Python worker accepted all job and desktop-isolation limits, rejected a local URL, exited, and refused to start after Stop. No web or model request was sent by this check."

    Copy-Item -LiteralPath $fileWorkerSource -Destination (Join-Path $buildRoot "file_operator.pyz") -Force
    $fileSelfTest = Start-Process -FilePath $builtExe -ArgumentList ('--file-self-test "' + $researchPythonPath + '"') -Wait -PassThru
    if ($fileSelfTest.ExitCode -ne 0) {
        throw "The desktop file worker failed its offline self-test with code $($fileSelfTest.ExitCode). No resident-host change was made."
    }
    Write-Host "[PASS] Owned file worker: Windows DPAPI, organize, verified undo and cooperative Stop rollback. Temporary fixtures only; no user folder permission was added."

    Copy-Item -LiteralPath $runtimeWorkerSource -Destination (Join-Path $buildRoot "runtime_worker.py") -Force
    $runtimeSelfTest = Start-Process -FilePath $builtExe -ArgumentList ('--runtime-self-test "' + $researchPythonPath + '"') -Wait -PassThru
    if ($runtimeSelfTest.ExitCode -ne 0) {
        throw "The runtime worker failed its offline self-test with code $($runtimeSelfTest.ExitCode). No resident-host change was made."
    }
    Write-Host "[PASS] Owned runtime worker: isolated imports, bounded offline status fixture and verified result. No live model request was made."

    Copy-Item -LiteralPath $documentWorkerSource -Destination (Join-Path $buildRoot "document_worker.pyz") -Force
    Copy-Item -LiteralPath $pdfParserSource -Destination (Join-Path $buildRoot "pdf_parser.pyz") -Force
    Copy-Item -LiteralPath $officeParserSource -Destination (Join-Path $buildRoot "office_parser.pyz") -Force
    $documentSelfTest = Start-Process -FilePath $builtExe -ArgumentList ('--document-self-test "' + $researchPythonPath + '"') -Wait -PassThru
    if ($documentSelfTest.ExitCode -ne 0) {
        throw "The document worker failed its offline self-test with code $($documentSelfTest.ExitCode). No resident-host change was made."
    }
    Write-Host "[PASS] Owned document worker: granted text/PDF/Office fixtures and synthetic PNG vision fixture; bounded citations and image checks. No live model request."

    if ($ValidationOnly) {
        Write-Host "[PASS] Validation-only run complete. Installed Cypher was not changed."
        return
    }

    $secure = (Get-Content -LiteralPath $legacyTokenPath -Raw).Trim() | ConvertTo-SecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $plainBytes = $null
    try {
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $plainBytes = [Text.Encoding]::UTF8.GetBytes($plainKey)
        $protectedBytes = [Security.Cryptography.ProtectedData]::Protect(
            $plainBytes,
            $null,
            [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        $protectedBase64 = [Convert]::ToBase64String($protectedBytes)

        $headers = @{ Authorization = "Bearer $plainKey" }
        $capabilities = Invoke-RestMethod -Uri "http://127.0.0.1:8642/v1/capabilities" -Headers $headers -Method Get -TimeoutSec 8
        foreach ($feature in @("run_submission", "run_status", "run_events_sse", "run_stop", "run_approval_response")) {
            if ($capabilities.features.$feature -ne $true) {
                throw "Hermes does not advertise '$feature'. Update Hermes before installing Cypher Core."
            }
        }
        Write-Host "[PASS] Hermes exposes authenticated runs, streaming, status, and cancellation."
    } finally {
        if ($plainBytes) { [Array]::Clear($plainBytes, 0, $plainBytes.Length) }
        if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
        $plainKey = $null
        $secure = $null
    }

    function Stop-LegacyHost {
        if (-not (Test-Path -LiteralPath $legacyHeartbeatPath -PathType Leaf)) { return }
        try {
            $heartbeat = Get-Content -LiteralPath $legacyHeartbeatPath -Raw | ConvertFrom-Json
            $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]$heartbeat.timestamp
            if ($age.TotalSeconds -lt -5 -or $age.TotalSeconds -gt 15) { return }
        } catch { return }
        Write-Host "[INFO] Stopping v0.6.3 cooperatively."
        [IO.File]::WriteAllText($legacyStopPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        do {
            if (-not (Test-Path -LiteralPath $legacyHeartbeatPath -PathType Leaf)) {
                Remove-Item -LiteralPath $legacyStopPath -Force -ErrorAction SilentlyContinue
                return
            }
            Start-Sleep -Milliseconds 400
        } while ([DateTime]::UtcNow -lt $deadline)
        throw "v0.6.3 did not stop within 15 seconds. Exit it from the tray and run this installer again."
    }

function Stop-ExistingPreviewHost {
    $owned = @(Get-Process -Name "CypherCoreHost" -ErrorAction SilentlyContinue | Where-Object {
        try { [string]::Equals($_.Path, $installedExe, [StringComparison]::OrdinalIgnoreCase) } catch { $false }
    })
    if ($owned.Count -eq 0) { return }
    $previewStatus = ""
    try {
        $heartbeat = Get-Content -LiteralPath $heartbeatPath -Raw | ConvertFrom-Json
        $age = [DateTimeOffset]::UtcNow - [DateTimeOffset]$heartbeat.timestamp
        if ($age.TotalSeconds -ge -5 -and $age.TotalSeconds -le 15) { $previewStatus = [string]$heartbeat.status }
    } catch { }
    if ($previewStatus -eq "working") {
        throw "Cypher has an active or recovering task. Use Ctrl+Alt+Space, stop it, and wait for a confirmed terminal state before upgrading."
    }
        Write-Host "[INFO] Stopping the installed Cypher Core preview cooperatively for upgrade."
        [IO.File]::WriteAllText($stopRequestPath, [DateTimeOffset]::UtcNow.ToString("o"), $utf8NoBom)
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        do {
            $remaining = @($owned | Where-Object { Get-Process -Id $_.Id -ErrorAction SilentlyContinue })
            if ($remaining.Count -eq 0) {
                Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
                return
            }
            Start-Sleep -Milliseconds 400
        } while ([DateTime]::UtcNow -lt $deadline)
        throw "The installed Cypher Core preview did not exit within 15 seconds. Stop any active task, exit it from the tray, then run this installer again."
    }

    Stop-ExistingPreviewHost
    Stop-LegacyHost
    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $rollbackRoot -Force | Out-Null
    if ((Test-Path -LiteralPath $shortcutPath -PathType Leaf) -and -not (Test-Path -LiteralPath $shortcutBackup -PathType Leaf)) {
        Copy-Item -LiteralPath $shortcutPath -Destination $shortcutBackup
    }
    $installedResearchWorker = Join-Path $installRoot "research_worker.py"
    Copy-Item -LiteralPath $researchWorkerSource -Destination $installedResearchWorker -Force
    if ((Get-FileHash -LiteralPath $installedResearchWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $researchWorkerHash) {
        throw "The installed research worker failed its integrity check; the executable was not replaced."
    }
    $installedVoiceWorker = Join-Path $installRoot "voice_worker.py"
    Copy-Item -LiteralPath $voiceWorkerSource -Destination $installedVoiceWorker -Force
    if ((Get-FileHash -LiteralPath $installedVoiceWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $voiceWorkerHash) {
        throw "The installed voice worker failed its integrity check; the executable was not replaced."
    }
    $installedFileWorker = Join-Path $installRoot "file_operator.pyz"
    Copy-Item -LiteralPath $fileWorkerSource -Destination $installedFileWorker -Force
    if ((Get-FileHash -LiteralPath $installedFileWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $fileWorkerHash) {
        throw "The installed file worker failed its integrity check; the executable was not replaced."
    }
    $installedRuntimeWorker = Join-Path $installRoot "runtime_worker.py"
    Copy-Item -LiteralPath $runtimeWorkerSource -Destination $installedRuntimeWorker -Force
    if ((Get-FileHash -LiteralPath $installedRuntimeWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $runtimeWorkerHash) {
        throw "The installed runtime worker failed its integrity check; the executable was not replaced."
    }
    $installedDocumentWorker = Join-Path $installRoot "document_worker.pyz"
    Copy-Item -LiteralPath $documentWorkerSource -Destination $installedDocumentWorker -Force
    if ((Get-FileHash -LiteralPath $installedDocumentWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $documentWorkerHash) {
        throw "The installed document worker failed its integrity check; the executable was not replaced."
    }
    $installedPdfParser = Join-Path $installRoot "pdf_parser.pyz"
    Copy-Item -LiteralPath $pdfParserSource -Destination $installedPdfParser -Force
    if ((Get-FileHash -LiteralPath $installedPdfParser -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pdfParserHash) {
        throw "The installed PDF parser failed its integrity check; the executable was not replaced."
    }
    $installedOfficeParser = Join-Path $installRoot "office_parser.pyz"
    Copy-Item -LiteralPath $officeParserSource -Destination $installedOfficeParser -Force
    if ((Get-FileHash -LiteralPath $installedOfficeParser -Algorithm SHA256).Hash.ToLowerInvariant() -ne $officeParserHash) {
        throw "The installed Office parser failed its integrity check; the executable was not replaced."
    }
    Copy-Item -LiteralPath $heroArtworkSource -Destination $installedHeroArtwork -Force
    if ((Get-FileHash -LiteralPath $installedHeroArtwork -Algorithm SHA256).Hash.ToLowerInvariant() -ne $heroArtworkHash) {
        throw "The installed Cypher signal artwork failed its integrity check; the executable was not replaced."
    }
    Copy-Item -LiteralPath $builtExe -Destination $installedExe -Force
    Copy-Item -LiteralPath $managerSource -Destination $installedManager -Force
    Copy-Item -LiteralPath $sourcePath -Destination $installedSource -Force
    foreach ($workflowSource in $workflowSources) {
        Copy-Item -LiteralPath $workflowSource -Destination (Join-Path $installRoot (Split-Path -Leaf $workflowSource)) -Force
    }
    $installedWakeWorker = Join-Path $installRoot "wake_worker.py"
    Copy-Item -LiteralPath $wakeWorkerSource -Destination $installedWakeWorker -Force
    if ((Get-FileHash -LiteralPath $installedWakeWorker -Algorithm SHA256).Hash.ToLowerInvariant() -ne $wakeWorkerHash) {
        throw "The installed wake worker failed its integrity check."
    }
    [IO.File]::WriteAllText($tokenPath, $protectedBase64, [Text.Encoding]::ASCII)

    $previousCloud = $null
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        try { $previousCloud = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json }
        catch { $previousCloud = $null }
    }
    $settings = [ordered]@{
        version = "0.7.0-core-preview10.21.0"
        assistant_name = $AssistantName
        endpoint = "http://127.0.0.1:8642"
        activation = "Ctrl+Alt+Space"
        default_mode = "auto"
        fast_model = "qwen3.5:9b-q4_K_M"
        deep_model = "gpt-oss:20b"
        vision_model = "qwen3.5:9b-q4_K_M"
        ollama_executable_path = $ollamaPath
        ollama_executable_sha256 = $ollamaHash
        research_python_path = $researchPythonPath
        voice_model_path = $voiceModelPath
        wake_python_path = $researchPythonPath
        wake_model_path = $wakeModelPath
        wake_deps_path = $wakeDepsPath
        wake_device_index = ""
        wake_device_name = ""
        wake_host_api = ""
        wake_phrase_score = 1.0
        wake_phrase_threshold = 0.25
        speech_voice_name = ""
        speech_rate = 0
        windows_apps_path = (Join-Path $env:LOCALAPPDATA "LocalAssistantBroker\windows_apps.json")
        microphone_enabled = $true
        wake_word_enabled = $true
        cloud_voice_enabled = $false
        cloud_max_audio_seconds_per_day = 600
        cloud_max_answers_per_day = 30
        content_logging = $false
        rollback_baseline = "0.6.3"
    }
    if ($previousCloud) {
        if (([string]$previousCloud.wake_device_index) -match '^\d{1,3}$' -and [int]$previousCloud.wake_device_index -le 128) {
            $settings.wake_device_index = [string]$previousCloud.wake_device_index
        }
        if (([string]$previousCloud.wake_device_name).Length -le 200 -and
            ([string]$previousCloud.wake_host_api).Length -le 200) {
            $settings.wake_device_name = [string]$previousCloud.wake_device_name
            $settings.wake_host_api = [string]$previousCloud.wake_host_api
        }
        if ($previousCloud.wake_phrase_score -ge 0.5 -and $previousCloud.wake_phrase_score -le 2.0) {
            $settings.wake_phrase_score = [double]$previousCloud.wake_phrase_score
        }
        if ($previousCloud.wake_phrase_threshold -ge 0.15 -and $previousCloud.wake_phrase_threshold -le 0.8) {
            $settings.wake_phrase_threshold = [double]$previousCloud.wake_phrase_threshold
        }
        if (([string]$previousCloud.speech_voice_name).Length -le 100) {
            $settings.speech_voice_name = [string]$previousCloud.speech_voice_name
        }
        $previousSpeechRate = 0
        if ([int]::TryParse([string]$previousCloud.speech_rate, [ref]$previousSpeechRate) -and
            $previousSpeechRate -ge -5 -and $previousSpeechRate -le 5) {
            $settings.speech_rate = $previousSpeechRate
        }
        if ($previousCloud.cloud_voice_enabled -eq $true -and (Test-Path -LiteralPath (Join-Path $installRoot "openai-cloud-key.dpapi"))) {
            $settings.cloud_voice_enabled = $true
        }
        if ($previousCloud.cloud_max_audio_seconds_per_day -ge 60 -and $previousCloud.cloud_max_audio_seconds_per_day -le 3600) {
            $settings.cloud_max_audio_seconds_per_day = [int]$previousCloud.cloud_max_audio_seconds_per_day
        }
        if ($previousCloud.cloud_max_answers_per_day -ge 1 -and $previousCloud.cloud_max_answers_per_day -le 200) {
            $settings.cloud_max_answers_per_day = [int]$previousCloud.cloud_max_answers_per_day
        }
    }
    [IO.File]::WriteAllText($configPath, ($settings | ConvertTo-Json -Depth 8), $utf8NoBom)

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $installedExe
    $shortcut.Arguments = ""
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.Description = "Cypher Core Preview 10.21.0 - hands-free voice preview"
    $shortcut.Save()

    Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $installedExe -WorkingDirectory $installRoot -WindowStyle Hidden
    $deadline = [DateTime]::UtcNow.AddSeconds(35)
    do {
        if (Test-Path -LiteralPath $heartbeatPath -PathType Leaf) { break }
        Start-Sleep -Milliseconds 400
    } while ([DateTime]::UtcNow -lt $deadline)
    if (-not (Test-Path -LiteralPath $heartbeatPath -PathType Leaf)) {
        if (Test-Path -LiteralPath $shortcutBackup -PathType Leaf) {
            Copy-Item -LiteralPath $shortcutBackup -Destination $shortcutPath -Force
        }
        $legacyManager = Join-Path $legacyRoot "manage_resident_host_windows.ps1"
        if (Test-Path -LiteralPath $legacyManager -PathType Leaf) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $legacyManager start
        }
        throw "The compiled host did not produce a heartbeat. The v0.6.3 login shortcut was restored."
    }

    Write-Host ""
    Write-Host "[PASS] Cypher Core Preview is running."
    Write-Host "Say Cypher or press Ctrl+Alt+Space for voice; press Ctrl+Win+Alt or use the tray to open chat."
    Write-Host "Safe, unambiguous Windows observations now use Cypher's deterministic local route."
    Write-Host "Exact registered-app launch, visible-window focus, and supported UI Automation patterns now use native one-time approval and verification."
    Write-Host "Exact AppUserModelID matching supports packaged apps; bounded SetValue text entry remains separately permissioned per app."
    Write-Host "Inspect one registered window's controls with: Show actionable controls in window ID <number>."
    Write-Host "Hermes remains the gated path for ambiguous, multi-step, or broader consequential tasks."
    Write-Host "Active tasks use metadata-only checkpoints and reconcile with Hermes after a host restart."
    Write-Host "Failed runs save only a content-free stage receipt at: $failureReceiptPath"
    Write-Host "Rollback manager: $installedManager"
} finally {
    Remove-Item -LiteralPath $buildRoot -Recurse -Force -ErrorAction SilentlyContinue
}
