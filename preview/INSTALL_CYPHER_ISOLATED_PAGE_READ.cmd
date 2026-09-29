@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$tokens = $null; $errors = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path '.\scripts\install_cypher_core_preview_windows.ps1').Path, [ref]$tokens, [ref]$errors); if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
if errorlevel 1 (
  echo.
  echo The installer failed its PowerShell parser check. Nothing was installed.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_cypher_core_preview_windows.ps1" -AssistantName "Cypher"
set "CYPHER_PAGE_READ_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_PAGE_READ_EXIT%"=="0" echo Cypher 10.3.0 Isolated Public Page Read was not installed. Review the error above.
if "%CYPHER_PAGE_READ_EXIT%"=="0" echo Cypher 10.3.0 Isolated Public Page Read installation finished successfully.
pause
exit /b %CYPHER_PAGE_READ_EXIT%
