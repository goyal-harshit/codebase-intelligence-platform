"""The ingestion pipeline, run in a background thread.

Steps mirror the master plan: cloning -> parsing -> building_graph ->
embedding -> risk_analysis -> complete. Each external step is guarded so a
missing service produces a clear failed/with-warning job rather than a crash.
"""
from __future__ import annotations

import os

from .config import Settings
from .jobs import JobManager


def clone_repo(repo_url: str, clone_dir: str) -> str:
    from git import Repo  # GitPython; imported lazily

    os.makedirs(clone_dir, exist_ok=True)
    name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = os.path.join(clone_dir, name)
    if not os.path.exists(dest):
        Repo.clone_from(repo_url, dest, depth=1)
    return dest


def run_ingestion(jobs: JobManager, job_id: str,
                  repo_url: str | None = None, repo_path: str | None = None) -> None:
    from ast_parser import parse_repository
    from graph_db import ArcadeDBClient, GraphBuilder, apply_schema

    try:
        # Check the graph DB BEFORE cloning — otherwise a large repo clones for
        # minutes only to fail because ArcadeDB isn't up.
        jobs.update(job_id, status="running", step="checking_services")
        graph = ArcadeDBClient()
        if not graph.is_alive():
            jobs.update(job_id, status="failed",
                        error=f"ArcadeDB not reachable at {graph.base_url}. "
                              f"Start the backing services (e.g. `docker compose up -d "
                              f"arcadedb chroma ollama`) before ingesting.")
            return

        path = repo_path
        if repo_url:
            jobs.update(job_id, step="cloning")
            path = clone_repo(repo_url, Settings().clone_dir)
        if not path or not os.path.isdir(path):
            jobs.update(job_id, status="failed", error=f"repo path not found: {path}")
            return

        # Full ingest is a clean rebuild: drop any prior graph so re-ingesting
        # the same repo doesn't hit duplicate-key errors (builder uses CREATE).
        if graph.database_exists():
            graph.drop_database()
        graph.create_database()
        apply_schema(graph)

        jobs.update(job_id, step="parsing")
        entities, relationships = parse_repository(path)

        jobs.update(job_id, step="building_graph")
        stats = GraphBuilder(graph).build(entities, relationships)

        jobs.update(job_id, step="embedding")
        try:
            from vector_db import VectorStoreBuilder
            VectorStoreBuilder().embed_and_store(entities)
        except Exception as e:  # Chroma/model optional — warn, keep going
            jobs.update(job_id, embed_warning=str(e))

        jobs.update(job_id, step="risk_analysis")
        n_risks = 0
        try:
            from risk_detection import RiskDetector, persist_risks
            risks = RiskDetector(graph).run_all_checks()
            n_risks = persist_risks(graph, risks)
        except Exception as e:
            jobs.update(job_id, risk_warning=str(e))

        jobs.update(job_id, status="complete", step="complete",
                    result={"entities": stats["entities"], "files": stats["files"],
                            "edges": stats["edges"], "risks": n_risks})
    except Exception as e:
        jobs.update(job_id, status="failed", error=str(e))
