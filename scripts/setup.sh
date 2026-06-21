#!/usr/bin/env bash
# First-run bootstrap: bring up the stack and pull the Ollama model.
set -euo pipefail

echo "==> Starting Ollama..."
docker compose up -d ollama
sleep 5

echo "==> Pulling the 'mistral' model (first run only, ~5GB)..."
docker compose exec -T ollama ollama pull mistral

echo "==> Starting the full stack..."
docker compose up -d --build

echo "==> Waiting for services to settle..."
sleep 15

echo "Done. Frontend: http://localhost:3000   API docs: http://localhost:8001/docs"
