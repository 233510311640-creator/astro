@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\configure_cypher_hermes_tools_windows.ps1"
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher Hermes tool configuration did not complete. Review the message above.
if "%CYPHER_EXIT%"=="0" echo Cypher Hermes tool configuration finished successfully.
pause
exit /b %CYPHER_EXIT%
