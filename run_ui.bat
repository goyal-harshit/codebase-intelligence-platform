@echo off
setlocal
title Codebase Intelligence Product UI
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
for /f %%P in ('powershell -NoProfile -Command "$p=8100; while(Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue){$p++}; $p"') do set "BACKEND_PORT=%%P"
for /f %%P in ('powershell -NoProfile -Command "$p=3100; while(Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue){$p++}; $p"') do set "FRONTEND_PORT=%%P"
set "API_URL=http://127.0.0.1:%BACKEND_PORT%"

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js / npm was not found on PATH.
  echo Install Node.js 20+ from https://nodejs.org/ and re-run this file.
  pause
  exit /b 1
)

if exist "%ROOT%\.venv\Scripts\python.exe" (
  set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python was not found on PATH and .venv is missing.
    pause
    exit /b 1
  )
  set "PYTHON=python"
)

if not exist "%ROOT%\frontend\node_modules" (
  echo [INFO] Installing frontend dependencies...
  pushd "%ROOT%\frontend"
  call npm install
  if errorlevel 1 (
    popd
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
  popd
)

where docker >nul 2>nul
if not errorlevel 1 (
  echo [INFO] Starting graph/vector backing services with Docker Compose...
  docker compose up -d arcadedb chroma
  if errorlevel 1 (
    echo [WARN] Could not start Docker services. Ingestion needs ArcadeDB on http://localhost:2480.
  )
) else (
  echo [WARN] Docker was not found. Ingestion needs ArcadeDB on http://localhost:2480.
)

echo.
echo ============================================================
echo   Codebase Intelligence Product UI
echo   Frontend: %FRONTEND_PORT%  http://127.0.0.1:%FRONTEND_PORT%
echo   Backend:  %BACKEND_PORT%  %API_URL%
echo.
echo   Keep both opened command windows running.
echo   If graph data is unavailable, start the backing services:
echo   docker compose up -d arcadedb chroma ollama postgres redis
echo ============================================================
echo.

start "Codebase Intelligence API %BACKEND_PORT%" /D "%ROOT%\backend" cmd /k "set CORS_ORIGIN_REGEX=^http://(localhost^|127\.0\.0\.1):(3[0-9][0-9][0-9]^|81[0-9][0-9])$&& "%PYTHON%" -m uvicorn main:app --reload --host 127.0.0.1 --port %BACKEND_PORT%"
start "Codebase Intelligence Frontend %FRONTEND_PORT%" /D "%ROOT%\frontend" cmd /k "set NEXT_PUBLIC_API_URL=%API_URL%&& npm run dev -- -H 127.0.0.1 -p %FRONTEND_PORT%"

timeout /t 5 >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"

echo Product UI launched at http://127.0.0.1:%FRONTEND_PORT%
echo Close the API and Frontend command windows to stop the project.
pause
