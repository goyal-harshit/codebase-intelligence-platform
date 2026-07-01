# First-run bootstrap (Windows): bring up the stack. Ollama is expected on
# the *host* (docker-compose.yml reaches it via host.docker.internal) --
# install it separately from https://ollama.com and pull the model there.
$ErrorActionPreference = "Stop"

try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Write-Host "==> Ollama detected on the host. Pulling 'qwen2.5-coder:7b' (first run only)..."
    ollama pull qwen2.5-coder:7b
} catch {
    Write-Host "==> WARNING: Ollama not detected on http://localhost:11434."
    Write-Host "    Install it from https://ollama.com, then run: ollama pull qwen2.5-coder:7b"
}

Write-Host "==> Starting the full stack..."
docker compose up -d --build

Write-Host "==> Waiting for services to settle..."
Start-Sleep -Seconds 15

Write-Host "Done. Frontend: http://localhost:3000   API docs: http://localhost:8001/docs"
