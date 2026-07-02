# ADR 0004: Ollama and open-weight LLMs (no paid model APIs)

## Status

Accepted (v1.0, shipped).

## Context

Q&A, Cypher generation, summarization, code review, and narrative reports all need an
LLM. Paid APIs (OpenAI, Anthropic) violate the ₹0 constraint, and a hosted dependency
would break local-first reproducibility. Open-weight code models (e.g.
`qwen2.5-coder:7b`) are good enough for grounded, retrieval-backed answers.

## Decision

Default to Ollama running on the host machine, reached from containers via
`http://host.docker.internal:11434/v1` (`LLM_BASE_URL` in `docker-compose.yml`; an
in-compose `ollama` service is provided commented-out). The access layer
(`backend/llm/`) is provider-flexible but free/local only:

- `ollama.py` — native Ollama client;
- `openai_compatible.py` — any OpenAI-compatible local server (LM Studio, llama.cpp,
  vLLM, text-generation-webui).

Both honour `LLM_BASE_URL` / `LLM_MODEL` (default model `qwen2.5-coder:7b`). Runtime
inspection/switching and model pulls are exposed at `/api/v1/llm-config`
(`backend/api/routes_llm.py`).

## Consequences

- Zero inference cost, no API keys, no data leaves the machine.
- Swapping models or runtimes is an env-var change, not a code change.
- Trade-off: quality and latency depend on local hardware; 7B-class models make
  mistakes that GPT/Claude-class models would not. Retrieval grounding and source
  citation (`backend/retrieval/answer.py`, `engine.py`) limit hallucination.
- No free GPU hosting exists, so cloud deployments must point `LLM_BASE_URL` at a
  user-operated machine or accept degraded (LLM-less) features.
