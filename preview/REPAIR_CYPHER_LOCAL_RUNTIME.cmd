@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\manage_cypher_local_runtime_windows.ps1" repair
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if "%CYPHER_EXIT%"=="2" echo Cypher local runtime repair was cancelled. No setting changed.
if not "%CYPHER_EXIT%"=="0" if not "%CYPHER_EXIT%"=="2" echo Cypher local runtime repair did not complete. If settings had begun changing, they were restored.
if "%CYPHER_EXIT%"=="0" echo Cypher local runtime repair finished successfully.
pause
exit /b %CYPHER_EXIT%
