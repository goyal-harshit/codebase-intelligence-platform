# Codebase Intelligence — first-time setup (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function OK($m)   { Write-Host "  [OK] $m"  -ForegroundColor Green }
function Warn($m) { Write-Host "  [!]  $m"  -ForegroundColor Yellow }
function Fail($m) { Write-Host "  [X]  $m"  -ForegroundColor Red; exit 1 }

Write-Host "=========================================="
Write-Host " Codebase Intelligence — Installer"
Write-Host "=========================================="

Write-Host "[1/5] Checking required software..."
if (Get-Command git -ErrorAction SilentlyContinue) { OK "Git $((git --version) -replace 'git version ','')" }
else { Fail "Git not found. Install from https://git-scm.com" }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Fail "Python not found. Install Python 3.11+ from https://python.org" }
$pyver = (python -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
if ([version]$pyver -lt [version]"3.11") { Fail "Python 3.11+ required (found $pyver)" }
OK "Python $pyver"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js not found. Install Node 20+ from https://nodejs.org" }
$nodever = (node -v).TrimStart('v')
if ([int]($nodever.Split('.')[0]) -lt 20) { Fail "Node.js 20+ required (found v$nodever)" }
OK "Node.js v$nodever"

if (Get-Command docker -ErrorAction SilentlyContinue) { OK "Docker $((docker --version) -replace 'Docker version ','' -replace ',.*','')" }
else { Warn "Docker not found (optional - needed for graph/vector services)" }

Write-Host "[2/5] Creating Python virtual environment..."
if (-not (Test-Path .venv)) { python -m venv .venv }
& .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
OK "Backend dependencies installed"

Write-Host "[3/5] Installing frontend dependencies..."
Push-Location frontend
npm install --silent
if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "npm install failed" }
Pop-Location
OK "Frontend dependencies installed"

Write-Host "[4/5] Configuring environment..."
if (-not (Test-Path .env)) { Copy-Item .env.example .env; OK "Created .env from .env.example" }
else { OK ".env already exists (unchanged)" }

Write-Host "[5/5] Preparing directories..."
New-Item -ItemType Directory -Force -Path logs, data | Out-Null
OK "logs\ and data\ ready"

Write-Host ""
Write-Host "Installation completed successfully." -ForegroundColor Green
Write-Host "Run .\run.ps1 to start.   (.\run.ps1 -Doctor to diagnose problems)"
