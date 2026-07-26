@echo off
REM Install the project dependencies using the PowerShell installer
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
