"""Repo ingestion via uploaded ZIP (Phase 3): an alternative to a Git URL.

Flow: receive a .zip -> archive the raw bytes in object storage -> extract it
safely to the clone dir -> enqueue the same durable ingestion task used by the
URL/path flow. Extraction is hardened against zip-slip (path traversal) and zip
bombs (uncompressed-size cap).
"""
from __future__ import annotations

import io
import os
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from .audit import record_audit
from .config import Settings
from .jobs import jobs
from .security import Principal, get_principal
from .tasks import ingest_repo_task

router = APIRouter()

# Defensive caps (overridable via env). Compressed cap bounds memory; the
# uncompressed cap bounds disk and defuses zip bombs.
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_UNCOMPRESSED_BYTES = int(os.getenv("MAX_UNCOMPRESSED_BYTES", str(500 * 1024 * 1024)))


def _safe_extract(zf: zipfile.ZipFile, dest: str) -> None:
    dest_abs = os.path.realpath(dest)
    total = 0
    for info in zf.infolist():
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise HTTPException(400, "archive too large when uncompressed")
        # Reject absolute paths and traversal that would escape dest.
        target = os.path.realpath(os.path.join(dest_abs, info.filename))
        if os.path.commonpath([dest_abs, target]) != dest_abs:
            raise HTTPException(400, f"unsafe path in archive: {info.filename}")
    zf.extractall(dest_abs)


@router.post("/ingest/upload")
async def ingest_upload(
    request: Request,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
):
    name = file.filename or ""
    if not name.lower().endswith(".zip"):
        raise HTTPException(400, "upload must be a .zip archive")

    data = await file.read()
    if not data:
        raise HTTPException(400, "empty upload")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"upload exceeds {MAX_UPLOAD_BYTES} bytes")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise HTTPException(400, "not a valid zip archive")

    uid = uuid.uuid4().hex
    # Archive the raw artifact (local fs by default, MinIO when configured).
    from storage import get_storage

    storage_locator = get_storage().put(f"uploads/{uid}.zip", data, content_type="application/zip")

    dest = os.path.join(Settings().clone_dir, "uploads", uid)
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        _safe_extract(zf, dest)

    job_id = jobs.create(repo_path=dest, user_id=principal.user_id)
    ingest_repo_task.delay(job_id, None, dest)
    record_audit(
        "ingest.upload",
        user_id=principal.user_id,
        target=name,
        detail={"job_id": job_id, "stored": storage_locator, "bytes": len(data)},
        request=request,
    )
    return {"job_id": job_id, "status": "queued"}
