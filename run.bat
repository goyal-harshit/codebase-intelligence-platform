@echo off
REM Run the project (backend + frontend) using the PowerShell launcher
powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
