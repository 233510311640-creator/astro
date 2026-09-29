@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\manage_cypher_local_runtime_windows.ps1" preflight
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher local runtime preflight failed. No setting was changed.
if "%CYPHER_EXIT%"=="0" echo Cypher local runtime preflight passed.
pause
exit /b %CYPHER_EXIT%
