"""Codebase Intelligence API (Phase 7).

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
Interactive docs at http://localhost:8000/docs
"""
import logging
import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api import (
    routes_impact,
    routes_ingest,
    routes_keys,
    routes_query,
    routes_repos,
    routes_risks,
    routes_stats,
)
from api.config import Settings
from api.ratelimit import SLOWAPI_AVAILABLE, limiter
from api.security import get_principal
from auth import (
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    fastapi_users,
)
from auth.users import AUTH_SECRET, DEV_SECRET
from observability import (
    REQUEST_ID_HEADER,
    configure_logging,
    metrics_payload,
    set_request_id,
)

configure_logging()
logger = logging.getLogger("codebase_intelligence")


def _load_env_local() -> None:
    """Load KEY=VALUE overrides from a gitignored .env.local at the repo root.

    Lets `uvicorn main:app` pick up machine-specific config (service ports,
    passwords, model name) without the launcher needing to set env vars.
    Real process env wins (setdefault), so it never clobbers explicit config.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_local()
settings = Settings()

app = FastAPI(
    title="Codebase Intelligence API",
    description="AI-powered architecture analysis for codebases",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (slowapi). app.state.limiter is required by the @limiter.limit
# decorators on the ingest/query routes; the handler turns over-limit into 429.
app.state.limiter = limiter
if SLOWAPI_AVAILABLE:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def _request_id_middleware(request: Request, call_next):
    """Attach a correlation id to every request (and its log records)."""
    rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
    set_request_id(rid)
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = rid
    return response


if not settings.api_key:
    logger.warning(
        "API_KEY is not set — all data endpoints are UNAUTHENTICATED. "
        "Set API_KEY before exposing this service beyond a trusted network."
    )

if AUTH_SECRET == DEV_SECRET:
    logger.warning(
        "AUTH_SECRET is the insecure dev default — set AUTH_SECRET to a strong "
        "random value before exposing user auth."
    )

# User auth (FastAPI-Users): registration, JWT login, and user management.
# These routes are intentionally NOT behind the API-key dependency.
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)

# Every data route requires a resolved principal (JWT, per-user API key, or the
# static service key) when API_KEY is configured. /health stays open for probes.
_auth = [Depends(get_principal)]
app.include_router(routes_ingest.router, prefix="/api/v1", tags=["ingest"], dependencies=_auth)
app.include_router(routes_query.router, prefix="/api/v1", tags=["query"], dependencies=_auth)
app.include_router(routes_impact.router, prefix="/api/v1", tags=["impact"], dependencies=_auth)
app.include_router(routes_risks.router, prefix="/api/v1", tags=["risks"], dependencies=_auth)
app.include_router(routes_stats.router, prefix="/api/v1", tags=["stats"], dependencies=_auth)
# Per-user API key management + repo RBAC (settings page). JWT-protected inside
# the routers, so they are not behind the service-key gate.
app.include_router(routes_keys.router, prefix="/api/v1", tags=["keys"])
app.include_router(routes_repos.router, prefix="/api/v1", tags=["repos"])


@app.on_event("startup")
def _init_database() -> None:
    """Create tables for local SQLite dev so the app runs with no setup.
    For Postgres, Alembic migrations are the source of truth (run separately)."""
    from db import get_database_url, init_db

    if get_database_url().startswith("sqlite"):
        init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus exposition (query latency, ingestion duration, LLM calls)."""
    payload = metrics_payload()
    if payload is None:
        raise HTTPException(503, "prometheus_client not installed")
    body, content_type = payload
    return Response(content=body, media_type=content_type)
