# Codebase Intelligence - deployment image.
# Runs the multi-page web app. Zero mandatory third-party deps; tree-sitter is
# installed for multi-language support but the app still works without it.
FROM python:3.11-slim

WORKDIR /app
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Optional deps: multi-language parsing. Failure here does not break the app
# (Python is analyzed via the stdlib ast fallback, graphs via the stdlib graph).
RUN pip install --no-cache-dir tree-sitter==0.21.3 tree-sitter-languages==1.10.2 || true

# git lets the "analyze a Git URL" feature clone repos.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8500
ENV LLM_BASE_URL=http://host.docker.internal:11434/v1 \
    LLM_MODEL=qwen2.5-coder:7b
# Bind 0.0.0.0 so the container is reachable from the host.
CMD ["python", "scripts/serve.py", "--host", "0.0.0.0", "--port", "8500", "--root", "/data"]
