@echo off
setlocal
title Codebase Intelligence UI
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup, then re-run this file.
  pause
  exit /b 1
)

REM No third-party packages are required - the analyzer runs on the Python
REM standard library alone. (tree-sitter only adds multi-language support and
REM is optional; Python projects work without it.)

start "" /b cmd /c "timeout /t 4 >nul & start "" http://127.0.0.1:8500"

echo.
echo ============================================================
echo   Codebase Intelligence UI
echo   Open in your browser:  http://127.0.0.1:8500
echo   (Keep this window open. Press Ctrl+C here to stop.)
echo ============================================================
echo.

python scripts\serve.py --port 8500 --host 127.0.0.1 --root "%ROOT%"

echo.
echo Server stopped. If you saw an error above, copy it and send it over.
pause
