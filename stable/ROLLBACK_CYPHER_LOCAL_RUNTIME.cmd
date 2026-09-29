@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\manage_cypher_local_runtime_windows.ps1" rollback
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if "%CYPHER_EXIT%"=="2" echo Cypher local runtime rollback was cancelled. No setting changed.
if not "%CYPHER_EXIT%"=="0" if not "%CYPHER_EXIT%"=="2" echo Cypher local runtime rollback did not complete. Review the message above.
if "%CYPHER_EXIT%"=="0" echo Cypher local runtime rollback finished successfully.
pause
exit /b %CYPHER_EXIT%
