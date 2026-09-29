@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage:
  echo   MANAGE_CYPHER_WINDOWS_APPS list
  echo   MANAGE_CYPHER_WINDOWS_APPS seed-builtins
  echo   MANAGE_CYPHER_WINDOWS_APPS add app-id "Display Name" "C:\Path\App.exe"
  echo   MANAGE_CYPHER_WINDOWS_APPS remove app-id
  echo   MANAGE_CYPHER_WINDOWS_APPS set-text-entry app-id on
  echo   MANAGE_CYPHER_WINDOWS_APPS set-text-entry app-id off
  echo   MANAGE_CYPHER_WINDOWS_APPS set-app-user-model-id app-id "PackageFamilyName!App"
  echo   MANAGE_CYPHER_WINDOWS_APPS set-app-user-model-id app-id none
  exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\manage_windows_apps_windows.ps1" %*
exit /b %ERRORLEVEL%
