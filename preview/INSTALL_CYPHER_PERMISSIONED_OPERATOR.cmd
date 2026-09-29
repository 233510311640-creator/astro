@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup_capability_broker_windows.ps1"
set "exit_code=%ERRORLEVEL%"
echo.
if not "%exit_code%"=="0" echo Cypher Permissioned Local Operator setup failed. No Hermes configuration was changed.
pause
exit /b %exit_code%
