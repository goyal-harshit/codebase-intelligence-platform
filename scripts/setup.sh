#!/usr/bin/env bash
# First-run bootstrap: bring up the stack. Ollama is expected on the *host*
# (docker-compose.yml reaches it via host.docker.internal) — install it
# separately from https://ollama.com and pull the model there, not in-compose.
set -euo pipefail

if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "==> Ollama detected on the host. Pulling 'qwen2.5-coder:7b' (first run only)..."
  ollama pull qwen2.5-coder:7b
else
  echo "==> WARNING: Ollama not detected on http://localhost:11434."
  echo "    Install it from https://ollama.com, then run: ollama pull qwen2.5-coder:7b"
fi

echo "==> Starting the full stack..."
docker compose up -d --build

echo "==> Waiting for services to settle..."
sleep 15

echo "Done. Frontend: http://localhost:3000   API docs: http://localhost:8001/docs"
