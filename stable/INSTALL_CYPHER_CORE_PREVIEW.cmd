@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_cypher_core_preview_windows.ps1" -AssistantName "Cypher"
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher Core Preview was not installed. Review the error above.
if "%CYPHER_EXIT%"=="0" echo Cypher Core Preview installation finished successfully.
pause
exit /b %CYPHER_EXIT%
