"""Per-repo role-based access control (FULL_STACK_GAP_PLAN.md Phase 2).

Roles are ordered ``viewer < member < owner``; a grant satisfies a requirement
when its rank is at least the required rank. Grants live in the ``repo_members``
table. A superuser bypasses repo membership checks entirely.

This module provides the storage helpers plus ``require_repo_role(min_role)``, a
FastAPI dependency factory that resolves the ``repo_id`` path parameter and 403s
when the caller lacks the required role.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status

import db as _db
from db import ROLE_ORDER, ROLE_OWNER, ROLE_VIEWER, Repo, RepoMember

from . import current_active_user


def role_rank(role: str) -> int:
    return ROLE_ORDER.index(role) if role in ROLE_ORDER else -1


def role_satisfies(have: Optional[str], need: str) -> bool:
    return have is not None and role_rank(have) >= role_rank(need)


def get_role(repo_id: str, user_id: str) -> Optional[str]:
    with _db.get_sessionmaker()() as s:
        row = (
            s.query(RepoMember)
            .filter(RepoMember.repo_id == repo_id, RepoMember.user_id == user_id)
            .first()
        )
        return row.role if row else None


def grant_role(repo_id: str, user_id: str, role: str) -> None:
    """Create or update a member's role on a repo (idempotent upsert)."""
    if role not in ROLE_ORDER:
        raise ValueError(f"unknown role: {role}")
    with _db.get_sessionmaker()() as s:
        row = (
            s.query(RepoMember)
            .filter(RepoMember.repo_id == repo_id, RepoMember.user_id == user_id)
            .first()
        )
        if row is None:
            s.add(RepoMember(repo_id=repo_id, user_id=user_id, role=role))
        else:
            row.role = role
        s.commit()


def revoke_member(repo_id: str, user_id: str) -> bool:
    with _db.get_sessionmaker()() as s:
        row = (
            s.query(RepoMember)
            .filter(RepoMember.repo_id == repo_id, RepoMember.user_id == user_id)
            .first()
        )
        if row is None:
            return False
        s.delete(row)
        s.commit()
        return True


def list_members(repo_id: str) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        rows = s.query(RepoMember).filter(RepoMember.repo_id == repo_id).all()
        return [{"user_id": r.user_id, "role": r.role, "created_at": r.created_at} for r in rows]


def create_repo(user_id: str, name: Optional[str] = None,
                url: Optional[str] = None, path: Optional[str] = None) -> dict:
    """Create a repo and grant its creator the ``owner`` role."""
    with _db.get_sessionmaker()() as s:
        repo = Repo(user_id=user_id, name=name, url=url, path=path)
        s.add(repo)
        s.flush()  # assign repo.id before creating the membership row
        s.add(RepoMember(repo_id=repo.id, user_id=user_id, role=ROLE_OWNER))
        s.commit()
        return {"id": repo.id, "name": repo.name, "url": repo.url, "path": repo.path}


def list_repos_for_user(user_id: str) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        rows = (
            s.query(Repo, RepoMember.role)
            .join(RepoMember, RepoMember.repo_id == Repo.id)
            .filter(RepoMember.user_id == user_id)
            .all()
        )
        return [
            {"id": r.id, "name": r.name, "url": r.url, "path": r.path, "role": role}
            for r, role in rows
        ]


@dataclass
class RepoContext:
    repo_id: str
    user_id: str
    role: str  # the caller's effective role ("owner" for superusers)


def require_repo_role(min_role: str = ROLE_VIEWER):
    """Dependency factory: require at least ``min_role`` on the path's repo_id."""

    def dependency(repo_id: str, user=Depends(current_active_user)) -> RepoContext:
        if getattr(user, "is_superuser", False):
            return RepoContext(repo_id=repo_id, user_id=user.id, role=ROLE_OWNER)
        role = get_role(repo_id, user.id)
        if not role_satisfies(role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires '{min_role}' role on this repo",
            )
        return RepoContext(repo_id=repo_id, user_id=user.id, role=role)

    return dependency
