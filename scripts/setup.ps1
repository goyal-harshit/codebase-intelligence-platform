# First-run bootstrap (Windows): bring up the stack and pull the Ollama model.
$ErrorActionPreference = "Stop"

Write-Host "==> Starting Ollama..."
docker compose up -d ollama
Start-Sleep -Seconds 5

Write-Host "==> Pulling the 'mistral' model (first run only, ~5GB)..."
docker compose exec -T ollama ollama pull mistral

Write-Host "==> Starting the full stack..."
docker compose up -d --build

Write-Host "==> Waiting for services to settle..."
Start-Sleep -Seconds 15

Write-Host "Done. Frontend: http://localhost:3000   API docs: http://localhost:8001/docs"
