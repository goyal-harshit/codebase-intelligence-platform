"""Codebase Intelligence API (Phase 7).

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
Interactive docs at http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    routes_impact,
    routes_ingest,
    routes_query,
    routes_risks,
    routes_stats,
)
from api.config import Settings

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

app.include_router(routes_ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(routes_query.router, prefix="/api/v1", tags=["query"])
app.include_router(routes_impact.router, prefix="/api/v1", tags=["impact"])
app.include_router(routes_risks.router, prefix="/api/v1", tags=["risks"])
app.include_router(routes_stats.router, prefix="/api/v1", tags=["stats"])


@app.get("/health")
def health():
    return {"status": "ok"}
