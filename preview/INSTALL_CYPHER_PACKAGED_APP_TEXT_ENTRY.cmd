@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$tokens = $null; $errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path '.\scripts\install_cypher_core_preview_windows.ps1').Path, [ref]$tokens, [ref]$errors); if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
if errorlevel 1 (
  echo.
  echo The Cypher installer failed its PowerShell parser preflight. Nothing was installed.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_cypher_core_preview_windows.ps1" -AssistantName "Cypher"
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher packaged-app text-entry preview was not installed. Review the error above.
if "%CYPHER_EXIT%"=="0" echo Cypher packaged-app text-entry preview installation finished successfully.
pause
exit /b %CYPHER_EXIT%
