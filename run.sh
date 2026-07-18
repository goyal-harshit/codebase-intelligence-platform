#!/usr/bin/env bash
# Codebase Intelligence — launcher (Linux/macOS)
# Usage: ./run.sh            local dev (hot reload)
#        ./run.sh --docker   full stack in Docker (production-like)
#        ./run.sh --doctor   environment diagnostics
set -euo pipefail
cd "$(dirname "$0")"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
err()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }

free_port() { # free_port <start>
  local p=$1
  while (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null; do exec 3>&- 3<&-; p=$((p+1)); done
  echo "$p"
}

doctor() {
  echo "=========================================="
  echo " Doctor — environment diagnostics"
  echo "=========================================="
  local bad=0
  command -v node >/dev/null 2>&1 && ok "Node $(node -v)" || { err "Node.js missing"; bad=1; }
  [ -x .venv/bin/python ] && ok "venv Python $(.venv/bin/python -V | awk '{print $2}')" || { err ".venv missing — run ./install.sh"; bad=1; }
  [ -d frontend/node_modules ] && ok "frontend/node_modules present" || { err "node_modules missing — run ./install.sh"; bad=1; }
  [ -f .env ] && ok ".env present" || { err ".env missing — run ./install.sh"; bad=1; }
  .venv/bin/python -c "import fastapi, uvicorn" 2>/dev/null && ok "backend imports resolve" || { err "backend deps broken — run ./install.sh"; bad=1; }
  if command -v docker >/dev/null 2>&1; then
    docker info >/dev/null 2>&1 && ok "Docker daemon running" || warn "Docker installed but daemon not running"
  else warn "Docker not installed (graph/vector services unavailable)"; fi
  curl -fsS http://localhost:2480 >/dev/null 2>&1 && ok "ArcadeDB reachable (2480)" || warn "ArcadeDB not reachable — ingestion disabled until 'docker compose up -d arcadedb chroma'"
  curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1 && ok "Ollama reachable (11434)" || warn "Ollama not reachable — LLM features disabled"
  [ $bad -eq 0 ] && echo "Result: healthy" || { echo "Result: problems found — fix ✗ items above"; exit 1; }
}

docker_deploy() {
  echo "=========================================="
  echo " Docker deploy — full stack"
  echo "=========================================="
  command -v docker >/dev/null 2>&1 || { err "Docker not found. Install from https://docker.com"; exit 1; }
  docker info >/dev/null 2>&1 || { err "Docker daemon not running. Start Docker and retry."; exit 1; }
  [ -f .env ] || { cp .env.example .env; ok "Created .env from .env.example — edit AUTH_SECRET for prod"; }
  if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    ok "Ollama detected — pulling model (first run only)"
    ollama pull qwen2.5-coder:7b || warn "Model pull failed; LLM features may be limited"
  else
    warn "Ollama not detected on :11434 — LLM features disabled (install from https://ollama.com)"
  fi
  echo "Building and starting: postgres, redis, minio, arcadedb, chroma, backend, worker, frontend..."
  docker compose up -d --build
  echo
  ok "Deployed.  Frontend http://localhost:3100 · API http://localhost:8001/docs"
  echo "  Logs: docker compose logs -f · Stop: docker compose down"
}

case "${1:-}" in
  --doctor) doctor; exit 0 ;;
  --docker) docker_deploy; exit 0 ;;
esac

echo "=========================================="
echo " Codebase Intelligence Launcher"
echo "=========================================="

# Health checks before launch
[ -x .venv/bin/python ] || { err ".venv missing. Run ./install.sh first."; exit 1; }
[ -d frontend/node_modules ] || { err "Frontend deps missing. Run ./install.sh first."; exit 1; }
[ -f .env ] || { warn ".env missing — creating from .env.example"; cp .env.example .env; }
ok "Dependencies verified"

# Backing services (optional)
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose up -d arcadedb chroma >/dev/null 2>&1 && ok "Backing services (ArcadeDB, Chroma) started" \
    || warn "Could not start backing services"
else
  warn "Docker unavailable — ingestion needs ArcadeDB on :2480"
fi

# Port detection
BACKEND_PORT=$(free_port 8100)
FRONTEND_PORT=$(free_port 3100)
ok "Backend port  $BACKEND_PORT"
ok "Frontend port $FRONTEND_PORT"

mkdir -p logs
TS=$(date +%Y%m%d-%H%M%S)

cleanup() {
  echo; echo "Stopping server..."
  [ -n "${BACK_PID:-}" ] && kill "$BACK_PID" 2>/dev/null || true
  [ -n "${FRONT_PID:-}" ] && kill "$FRONT_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  echo "Cleaning resources... Done."
}
trap cleanup INT TERM EXIT

echo "Starting backend..."
( cd backend && CORS_ORIGIN_REGEX='^http://(localhost|127\.0\.0\.1):(3[0-9]{3}|81[0-9]{2})$' \
  ../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
  >"../logs/backend-$TS.log" 2>&1 ) & BACK_PID=$!

echo "Starting frontend..."
( cd frontend && NEXT_PUBLIC_API_URL="http://127.0.0.1:$BACKEND_PORT" \
  npm run dev -- -H 127.0.0.1 -p "$FRONTEND_PORT" \
  >"../logs/frontend-$TS.log" 2>&1 ) & FRONT_PID=$!

sleep 5
echo
echo "✓ Running at   http://127.0.0.1:$FRONTEND_PORT"
echo "  API docs     http://127.0.0.1:$BACKEND_PORT/docs"
echo "  Logs         logs/backend-$TS.log · logs/frontend-$TS.log"
echo "  Press Ctrl+C to stop."
wait
