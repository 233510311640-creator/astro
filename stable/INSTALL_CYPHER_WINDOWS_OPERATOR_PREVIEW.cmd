@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_cypher_windows_operator_preview_windows.ps1"
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher Windows Operator Preview installation did not complete.
if "%CYPHER_EXIT%"=="0" echo Cypher Windows Operator Preview installation finished successfully.
pause
exit /b %CYPHER_EXIT%
