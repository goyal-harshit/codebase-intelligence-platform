@echo off
setlocal
title Codebase Intelligence - Docker Deploy
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ============================================================
echo   Codebase Intelligence - One-Click Docker Deploy
echo ============================================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker was not found on PATH.
  echo Install Docker Desktop from https://www.docker.com/products/docker-desktop
  echo then re-run this file.
  pause
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker Compose plugin was not found.
  echo Update Docker Desktop to a recent version and re-run this file.
  pause
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker Desktop does not appear to be running.
  echo Start Docker Desktop and re-run this file.
  pause
  exit /b 1
)

if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" (
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo [INFO] Created .env from .env.example with default values.
    echo [INFO] Edit .env to set a real AUTH_SECRET / GitHub OAuth keys, then re-run if needed.
    echo.
  )
)

echo [INFO] Building and starting the full stack: postgres, redis, minio,
echo        arcadedb, chroma, backend, worker, frontend.
echo        First run downloads/builds images and can take several minutes.
echo.
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo [ERROR] Docker deployment failed. See errors above.
  pause
  exit /b 1
)

echo.
echo [INFO] Waiting for services to finish starting...
timeout /t 10 >nul

echo.
echo ============================================================
echo   Deployed.
echo   Frontend: http://localhost:3100
echo   Backend:  http://localhost:8001
echo   MinIO console: http://localhost:9001
echo   ArcadeDB:      http://localhost:2480
echo.
echo   Logs:   docker compose logs -f
echo   Status: docker compose ps
echo   Stop:   docker compose down          (keeps data volumes)
echo   Reset:  docker compose down -v       (WIPES all data volumes)
echo.
echo   For local dev with hot reload instead, use run_local.bat.
echo ============================================================
echo.

start "" "http://localhost:3100"
pause
