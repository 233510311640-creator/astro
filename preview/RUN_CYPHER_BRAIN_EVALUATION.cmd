@echo off
setlocal
title Cypher v0.7 Brain Evaluation
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_cypher_brain_evaluation_windows.ps1"
set "CYPHER_EXIT=%ERRORLEVEL%"
echo.
if not "%CYPHER_EXIT%"=="0" echo Cypher preflight stopped with exit code %CYPHER_EXIT%.
pause
exit /b %CYPHER_EXIT%
