"""Per-user API key management (the "settings page" backend).

All routes require a logged-in user (JWT). A user only ever sees and manages
their own keys. The raw secret is returned exactly once, on creation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth import current_active_user
from auth.apikeys import create_api_key, list_api_keys, revoke_api_key

from .audit import record_audit

router = APIRouter()


class ApiKeyCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class ApiKeyInfo(BaseModel):
    id: str
    name: Optional[str] = None
    revoked: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyCreated(ApiKeyInfo):
    # Present only in the create response; never retrievable again.
    key: str


@router.post("/keys", response_model=ApiKeyCreated, status_code=201)
def create_key(body: ApiKeyCreate, request: Request, user=Depends(current_active_user)):
    raw, meta = create_api_key(user.id, name=body.name)
    record_audit("apikey.create", user_id=user.id, target=meta["id"], request=request)
    return {**meta, "key": raw}


@router.get("/keys", response_model=list[ApiKeyInfo])
def list_keys(user=Depends(current_active_user)):
    return list_api_keys(user.id)


@router.delete("/keys/{key_id}", status_code=204)
def delete_key(key_id: str, request: Request, user=Depends(current_active_user)):
    if not revoke_api_key(user.id, key_id):
        raise HTTPException(404, "unknown or already-revoked key")
    record_audit("apikey.revoke", user_id=user.id, target=key_id, request=request)
