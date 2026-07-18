# Codebase Intelligence — launcher (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File run.ps1 [-Doctor]
param([switch]$Doctor)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function OK($m)   { Write-Host "  [OK] $m"  -ForegroundColor Green }
function Warn($m) { Write-Host "  [!]  $m"  -ForegroundColor Yellow }
function Err($m)  { Write-Host "  [X]  $m"  -ForegroundColor Red }

function Get-FreePort([int]$start) {
  $p = $start
  while (Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue) { $p++ }
  return $p
}

function Test-Url($url) {
  try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null; $true } catch { $false }
}

if ($Doctor) {
  Write-Host "=========================================="
  Write-Host " Doctor — environment diagnostics"
  Write-Host "=========================================="
  $bad = $false
  if (Get-Command node -ErrorAction SilentlyContinue) { OK "Node $(node -v)" } else { Err "Node.js missing"; $bad = $true }
  if (Test-Path .venv\Scripts\python.exe) { OK "venv Python $(& .venv\Scripts\python.exe -V)" } else { Err ".venv missing - run install.ps1"; $bad = $true }
  if (Test-Path frontend\node_modules) { OK "frontend\node_modules present" } else { Err "node_modules missing - run install.ps1"; $bad = $true }
  if (Test-Path .env) { OK ".env present" } else { Err ".env missing - run install.ps1"; $bad = $true }
  & .venv\Scripts\python.exe -c "import fastapi, uvicorn" 2>$null
  if ($LASTEXITCODE -eq 0) { OK "backend imports resolve" } else { Err "backend deps broken - run install.ps1"; $bad = $true }
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { OK "Docker daemon running" } else { Warn "Docker installed but daemon not running" }
  } else { Warn "Docker not installed (graph/vector services unavailable)" }
  if (Test-Url "http://localhost:2480") { OK "ArcadeDB reachable (2480)" } else { Warn "ArcadeDB not reachable - ingestion disabled until 'docker compose up -d arcadedb chroma'" }
  if (Test-Url "http://localhost:11434/api/tags") { OK "Ollama reachable (11434)" } else { Warn "Ollama not reachable - LLM features disabled" }
  if ($bad) { Write-Host "Result: problems found - fix [X] items above"; exit 1 }
  Write-Host "Result: healthy"; exit 0
}

Write-Host "=========================================="
Write-Host " Codebase Intelligence Launcher"
Write-Host "=========================================="

if (-not (Test-Path .venv\Scripts\python.exe)) { Err ".venv missing. Run install.ps1 first."; exit 1 }
if (-not (Test-Path frontend\node_modules))    { Err "Frontend deps missing. Run install.ps1 first."; exit 1 }
if (-not (Test-Path .env)) { Warn ".env missing - creating from .env.example"; Copy-Item .env.example .env }
OK "Dependencies verified"

if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker compose up -d arcadedb chroma 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { OK "Backing services (ArcadeDB, Chroma) started" } else { Warn "Could not start backing services" }
} else { Warn "Docker unavailable - ingestion needs ArcadeDB on :2480" }

$BackendPort  = Get-FreePort 8100
$FrontendPort = Get-FreePort 3100
OK "Backend port  $BackendPort"
OK "Frontend port $FrontendPort"

New-Item -ItemType Directory -Force -Path logs | Out-Null
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$root = $PSScriptRoot

# Children inherit these (works on Windows PowerShell 5.1 and PowerShell 7+)
$env:CORS_ORIGIN_REGEX  = '^http://(localhost|127\.0\.0\.1):(3[0-9]{3}|81[0-9]{2})$'
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$BackendPort"

$backend = Start-Process -PassThru -WindowStyle Hidden -FilePath "$root\.venv\Scripts\python.exe" `
  -WorkingDirectory "$root\backend" `
  -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","$BackendPort" `
  -RedirectStandardOutput "$root\logs\backend-$ts.log" -RedirectStandardError "$root\logs\backend-$ts.err.log"

$frontend = Start-Process -PassThru -WindowStyle Hidden -FilePath "cmd.exe" `
  -WorkingDirectory "$root\frontend" `
  -ArgumentList "/c","npm run dev -- -H 127.0.0.1 -p $FrontendPort" `
  -RedirectStandardOutput "$root\logs\frontend-$ts.log" -RedirectStandardError "$root\logs\frontend-$ts.err.log"

Start-Sleep -Seconds 5
Write-Host ""
Write-Host "Running at   http://127.0.0.1:$FrontendPort" -ForegroundColor Green
Write-Host "API docs     http://127.0.0.1:$BackendPort/docs"
Write-Host "Logs         logs\backend-$ts.log  logs\frontend-$ts.log"
Write-Host "Press Ctrl+C to stop."
Start-Process "http://127.0.0.1:$FrontendPort"

try {
  Wait-Process -Id $backend.Id, $frontend.Id
} finally {
  Write-Host ""; Write-Host "Stopping server..."
  foreach ($p in @($backend, $frontend)) {
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  }
  # Kill child node processes spawned by cmd wrapper
  Get-CimInstance Win32_Process -Filter "ParentProcessId = $($frontend.Id)" -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Write-Host "Cleaning resources... Done."
}
