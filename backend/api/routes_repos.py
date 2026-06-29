"""Repo ownership + membership management (Phase 2 RBAC).

A repo's creator becomes its ``owner``. Owners manage membership; any member
(viewer+) can list a repo and its members. Roles are ``viewer < member < owner``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import db as _db
from auth import current_active_user
from auth.rbac import (
    RepoContext,
    create_repo,
    grant_role,
    list_members,
    list_repos_for_user,
    require_repo_role,
)
from db import ROLE_ORDER, ROLE_OWNER, User

from .audit import record_audit

router = APIRouter()


class RepoCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    url: Optional[str] = Field(default=None, max_length=2048)
    path: Optional[str] = Field(default=None, max_length=2048)


class RepoInfo(BaseModel):
    id: str
    name: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None
    role: Optional[str] = None


class MemberInfo(BaseModel):
    user_id: str
    role: str
    created_at: datetime


class MemberGrant(BaseModel):
    user_id: str
    role: str = Field(description="one of: viewer, member, owner")


@router.post("/repos", response_model=RepoInfo, status_code=201)
def create_repo_route(body: RepoCreate, request: Request, user=Depends(current_active_user)):
    repo = create_repo(user.id, name=body.name, url=body.url, path=body.path)
    record_audit("repo.create", user_id=user.id, target=repo["id"], request=request)
    return {**repo, "role": ROLE_OWNER}


@router.get("/repos", response_model=list[RepoInfo])
def list_repos_route(user=Depends(current_active_user)):
    return list_repos_for_user(user.id)


@router.get("/repos/{repo_id}/members", response_model=list[MemberInfo])
def list_members_route(ctx: RepoContext = Depends(require_repo_role())):
    return list_members(ctx.repo_id)


@router.put("/repos/{repo_id}/members", response_model=list[MemberInfo])
def add_member_route(
    body: MemberGrant,
    request: Request,
    ctx: RepoContext = Depends(require_repo_role(ROLE_OWNER)),
):
    if body.role not in ROLE_ORDER:
        raise HTTPException(400, f"role must be one of {list(ROLE_ORDER)}")
    with _db.get_sessionmaker()() as s:
        if s.get(User, body.user_id) is None:
            raise HTTPException(404, "unknown user_id")
    grant_role(ctx.repo_id, body.user_id, body.role)
    record_audit(
        "repo.member.grant",
        user_id=ctx.user_id,
        target=ctx.repo_id,
        detail={"member": body.user_id, "role": body.role},
        request=request,
    )
    return list_members(ctx.repo_id)


@router.delete("/repos/{repo_id}/members/{member_id}", status_code=204)
def remove_member_route(
    member_id: str,
    request: Request,
    ctx: RepoContext = Depends(require_repo_role(ROLE_OWNER)),
):
    from auth.rbac import revoke_member

    if member_id == ctx.user_id:
        raise HTTPException(400, "owners cannot remove themselves; transfer ownership first")
    if not revoke_member(ctx.repo_id, member_id):
        raise HTTPException(404, "user is not a member of this repo")
    record_audit(
        "repo.member.revoke",
        user_id=ctx.user_id,
        target=ctx.repo_id,
        detail={"member": member_id},
        request=request,
    )
