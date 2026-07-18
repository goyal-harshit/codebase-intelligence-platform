#!/usr/bin/env bash
# Codebase Intelligence — first-time setup (Linux/macOS)
# Usage: ./install.sh
set -euo pipefail
cd "$(dirname "$0")"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$1"; exit 1; }

echo "=========================================="
echo " Codebase Intelligence — Installer"
echo "=========================================="

echo "[1/5] Checking required software..."
command -v git >/dev/null 2>&1 && ok "Git $(git --version | awk '{print $3}')" \
  || fail "Git not found. Install from https://git-scm.com"

command -v python3 >/dev/null 2>&1 && PY=python3 || PY=python
command -v "$PY" >/dev/null 2>&1 || fail "Python not found. Install Python 3.11+ from https://python.org"
PYVER=$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' \
  && ok "Python $PYVER" || fail "Python 3.11+ required (found $PYVER)"

command -v node >/dev/null 2>&1 || fail "Node.js not found. Install Node 20+ from https://nodejs.org"
NODEVER=$(node -v | tr -d 'v')
[ "${NODEVER%%.*}" -ge 20 ] && ok "Node.js v$NODEVER" || fail "Node.js 20+ required (found v$NODEVER)"

command -v docker >/dev/null 2>&1 && ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')" \
  || warn "Docker not found (optional — needed for graph/vector services)"

echo "[2/5] Creating Python virtual environment..."
if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r backend/requirements.txt
ok "Backend dependencies installed"

echo "[3/5] Installing frontend dependencies..."
( cd frontend && npm install --silent )
ok "Frontend dependencies installed"

echo "[4/5] Configuring environment..."
if [ ! -f .env ]; then cp .env.example .env; ok "Created .env from .env.example"; else ok ".env already exists (unchanged)"; fi

echo "[5/5] Preparing directories..."
mkdir -p logs data
ok "logs/ and data/ ready"

echo
echo "✓ Installation completed successfully."
echo "  Run ./run.sh to start.   (./run.sh --doctor to diagnose problems)"
