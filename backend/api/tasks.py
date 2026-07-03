"""The ingestion pipeline, dispatched as a durable Celery task.

Steps mirror the master plan: cloning -> parsing -> building_graph ->
embedding -> risk_analysis -> complete. Each external step is guarded so a
missing service produces a clear failed/with-warning job rather than a crash.
Job state is persisted via the DB-backed JobManager so it survives a restart
and is shared between the API process and the worker.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time

import requests

from celery_app import ALWAYS_EAGER, celery_app
from observability import INGESTION_DURATION

from .config import Settings
from .jobs import JobManager, jobs

logger = logging.getLogger("codebase_intelligence.ingest")


@celery_app.task(name="ingest_repo")
def ingest_repo_task(job_id: str, repo_url: str | None = None,
                     repo_path: str | None = None) -> None:
    """Celery entry point. Runs eagerly (in-process) when no broker is set."""
    run_ingestion(jobs, job_id, repo_url, repo_path)


def dispatch_ingest(job_id: str, repo_url: str | None = None,
                    repo_path: str | None = None) -> None:
    """Kick off an ingestion without blocking the HTTP request.

    In eager mode (dev default) ``.delay()`` runs the whole minutes-long
    pipeline synchronously inside the request thread — the caller's POST hangs
    and the CPU-bound work starves everything else (notably local LLM calls).
    Same workaround as ``dispatch_model_pull``: daemon thread when eager,
    worker dispatch otherwise.
    """
    if ALWAYS_EAGER:
        threading.Thread(
            target=run_ingestion, args=(jobs, job_id, repo_url, repo_path),
            daemon=True,
        ).start()
    else:
        ingest_repo_task.delay(job_id, repo_url, repo_path)


# --- Local model pull (Ollama) -------------------------------------------

@celery_app.task(name="pull_model")
def pull_model_task(model: str, user_id: str | None = None) -> None:
    run_model_pull(model, user_id)


def dispatch_model_pull(model: str, user_id: str | None) -> None:
    """Kick off a model pull without blocking the HTTP request.

    In eager mode (dev default) ``.delay()`` would run synchronously and block
    the request for the whole (minutes-long) download, so run it in a daemon
    thread instead. With a real broker, hand it to the worker.
    """
    if ALWAYS_EAGER:
        threading.Thread(target=run_model_pull, args=(model, user_id), daemon=True).start()
    else:
        pull_model_task.delay(model, user_id)


def _notify(user_id: str | None, title: str, *, level: str = "info",
            body: str | None = None, detail: dict | None = None) -> None:
    if not user_id:
        return
    try:
        from notifications import create_notification

        create_notification(user_id, title, level=level, type="model_pull",
                            body=body, detail=detail)
    except Exception:  # noqa: BLE001 - notifications must never fail the pull
        logger.warning("model-pull notification failed", exc_info=True)


def run_model_pull(model: str, user_id: str | None = None) -> None:
    """Stream ``POST /api/pull`` from Ollama, reporting progress as notifications.

    Progress is throttled to one notification per 10% bucket (plus status
    changes) so the WebSocket/notification store isn't flooded on large pulls.
    """
    from llm import config as llm_config

    base_url = llm_config.effective_config()["base_url"].rstrip("/")
    _notify(user_id, f"Pulling model {model}", detail={"model": model, "status": "starting"})
    last_bucket = -1
    last_status = ""
    try:
        with requests.post(f"{base_url}/api/pull", json={"model": model, "stream": True},
                           stream=True, timeout=3600) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except ValueError:
                    continue
                if evt.get("error"):
                    _notify(user_id, f"Model pull failed: {model}", level="error",
                            body=str(evt["error"]), detail={"model": model})
                    return
                status = evt.get("status", "")
                total, completed = evt.get("total"), evt.get("completed")
                if total and completed:
                    bucket = int(completed * 10 / total)
                    if bucket != last_bucket:
                        last_bucket = bucket
                        _notify(user_id, f"Pulling {model}: {bucket * 10}%",
                                detail={"model": model, "percent": bucket * 10, "status": status})
                elif status and status != last_status:
                    last_status = status
                    _notify(user_id, f"Pulling {model}: {status}",
                            detail={"model": model, "status": status})
        _notify(user_id, f"Model ready: {model}", level="success",
                detail={"model": model, "status": "complete"})
    except Exception as e:  # noqa: BLE001 - surface any failure to the user
        logger.warning("model pull for %s failed: %s", model, e)
        _notify(user_id, f"Model pull failed: {model}", level="error",
                body=str(e), detail={"model": model})


def clone_repo(repo_url: str, clone_dir: str) -> str:
    from git import Repo  # GitPython; imported lazily

    os.makedirs(clone_dir, exist_ok=True)
    name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = os.path.join(clone_dir, name)
    if not os.path.exists(dest):
        Repo.clone_from(repo_url, dest, depth=1)
    return dest


def _notify(jobs: JobManager, job_id: str) -> None:
    """Fan a job's (already-persisted) terminal state out to in-app + email
    notifications. Best-effort: notifications must never fail the job."""
    try:
        from notifications import notify_job_completion

        job = jobs.get(job_id)
        if not job:
            return
        notify_job_completion(job_id, job.get("user_id"), job["status"],
                              result=job.get("result"), error=job.get("error"))
    except Exception:
        logger.warning("[job %s] notification dispatch failed", job_id, exc_info=True)


def _invalidate_analysis_caches() -> None:
    """Drop cached analysis results so a fresh ingest is reflected immediately
    instead of serving stale stats/risks/hotspots/refactor/security. Best-effort:
    a cache miss must never fail the ingest."""
    try:
        from .result_cache import invalidate
        invalidate()
    except Exception:  # noqa: BLE001
        logger.warning("analysis cache invalidation failed", exc_info=True)
    try:
        from .routes_security import _scan_cache
        _scan_cache.clear()
    except Exception:  # noqa: BLE001
        logger.warning("security scan cache invalidation failed", exc_info=True)


# Default request params the frontend uses, so warming populates the exact cache
# keys the pages will read (dashboard asks hotspots limit=12; refactor page uses
# the route default limit=100).
_WARM_HOTSPOTS_LIMIT = 12
_WARM_REFACTOR_LIMIT = 100


def _warm_analysis_caches(repo_path: str | None) -> None:
    """Pre-compute every analysis result the dashboard and analysis pages read,
    so the first visit to each page is instant instead of triggering a full
    graph/git/SAST recompute. Runs after an ingest completes. Each step is
    isolated: one backend being down must not stop the others (or the ingest)."""
    from .deps import get_graph_client
    from . import routes_hotspots, routes_refactor, routes_risks, routes_security, routes_stats

    try:
        graph = get_graph_client()
    except Exception:  # noqa: BLE001
        logger.warning("[warm] graph client unavailable; skipping warm", exc_info=True)
        return

    steps: list[tuple[str, callable]] = [
        ("stats", lambda: routes_stats.cached_stats(graph)),
        ("risks", lambda: routes_risks.cached_risks(graph)),
        ("refactor", lambda: routes_refactor.cached_refactor(graph, _WARM_REFACTOR_LIMIT)),
    ]
    if repo_path and os.path.isdir(repo_path):
        steps.append(("hotspots", lambda: routes_hotspots.cached_hotspots(graph, repo_path, _WARM_HOTSPOTS_LIMIT)))
        steps.append(("security", lambda: routes_security.scan_cached(repo_path)))

    for label, fn in steps:
        try:
            fn()
            logger.info("[warm] %s cache warmed", label)
        except Exception:  # noqa: BLE001
            logger.warning("[warm] %s failed", label, exc_info=True)


def _warm_analysis_caches_async(repo_path: str | None) -> None:
    """Warm caches off the ingest thread so job completion / notifications aren't
    delayed by the (slow) SAST scan."""
    threading.Thread(target=_warm_analysis_caches, args=(repo_path,), daemon=True).start()


def run_ingestion(jobs: JobManager, job_id: str,
                  repo_url: str | None = None, repo_path: str | None = None) -> None:
    from ast_parser import parse_repository
    from graph_db import ArcadeDBClient, GraphBuilder, apply_schema

    _start = time.perf_counter()
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
            _notify(jobs, job_id)
            return

        path = repo_path
        if repo_url:
            jobs.update(job_id, step="cloning")
            path = clone_repo(repo_url, Settings().clone_dir)
            jobs.update(job_id, repo_path=path)
        if not path or not os.path.isdir(path):
            jobs.update(job_id, status="failed", error=f"repo path not found: {path}")
            _notify(jobs, job_id)
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

        warnings: list[str] = []

        jobs.update(job_id, step="embedding")
        try:
            from vector_db import VectorStoreBuilder
            VectorStoreBuilder().embed_and_store(entities)
        except Exception as e:  # Chroma/model optional — warn, keep going
            warnings.append(f"embedding: {e}")
            logger.warning("[job %s] embedding step failed: %s", job_id, e)

        jobs.update(job_id, step="risk_analysis")
        n_risks = 0
        try:
            from risk_detection import RiskDetector, persist_risks
            risks = RiskDetector(graph).run_all_checks()
            n_risks = persist_risks(graph, risks)
        except Exception as e:
            warnings.append(f"risk_analysis: {e}")
            logger.warning("[job %s] risk analysis failed: %s", job_id, e)

        # A job that skipped embedding or risk analysis is NOT a clean success —
        # surface that so callers don't trust an incomplete index.
        final_status = "complete_with_warnings" if warnings else "complete"
        jobs.update(job_id, status=final_status, step="complete", warnings=warnings,
                    result={"entities": stats["entities"], "files": stats["files"],
                            "edges": stats["edges"], "risks": n_risks})
        logger.info("[job %s] ingestion %s (%s files, %s risks)",
                    job_id, final_status, stats["files"], n_risks)
        _invalidate_analysis_caches()
        _notify(jobs, job_id)
        # Proactively compute every page's data now so users don't have to visit
        # each page to trigger it — the whole workspace is ready on completion.
        _warm_analysis_caches_async(path)
    except Exception as e:
        jobs.update(job_id, status="failed", error=str(e))
        logger.error("[job %s] ingestion failed: %s", job_id, e)
        _notify(jobs, job_id)
    finally:
        INGESTION_DURATION.observe(time.perf_counter() - _start)
