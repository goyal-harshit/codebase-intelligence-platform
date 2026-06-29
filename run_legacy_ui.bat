@echo off
setlocal
title Codebase Intelligence Legacy UI
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  pause
  exit /b 1
)

start "" /b cmd /c "timeout /t 4 >nul & start "" http://127.0.0.1:8500"

echo.
echo ============================================================
echo   Codebase Intelligence Legacy Python UI
echo   Open in your browser:  http://127.0.0.1:8500
echo ============================================================
echo.

python scripts\serve.py --port 8500 --host 127.0.0.1 --root "%ROOT%"

echo.
echo Server stopped. If you saw an error above, copy it and send it over.
pause
