"""Relational metadata models: users, api_keys, jobs, repos, audit_log.

Portable across SQLite (dev/test) and PostgreSQL (prod): string UUID primary
keys, the generic JSON type, and timezone-aware UTC timestamps. This is the
"single biggest structural gap" identified in FULL_STACK_GAP_PLAN.md §2 — the
place to put users, durable job state, and audit logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base

# RBAC roles, least to most privileged. A higher-privileged role implies the
# capabilities of every role below it (see auth.rbac.role_satisfies).
ROLE_VIEWER = "viewer"
ROLE_MEMBER = "member"
ROLE_OWNER = "owner"
ROLE_ORDER = (ROLE_VIEWER, ROLE_MEMBER, ROLE_OWNER)


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLAlchemyBaseUserTable[str], Base):
    """User account.

    Inherits ``email``, ``hashed_password``, ``is_active``, ``is_superuser`` and
    ``is_verified`` from FastAPI-Users' base table; we add the string-UUID id
    (to match the FK columns on the other tables) plus profile/OAuth fields.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # OAuth identity (provider + subject), null for password accounts.
    oauth_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    repos: Mapped[list["Repo"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Store only a hash of the key, never the raw secret.
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")


class Job(Base):
    __tablename__ = "jobs"

    # Primary key is the public job_id (uuid hex), matching the existing API.
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    repo_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSON, default=list)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User | None"] = relationship(back_populates="repos")
    members: Mapped[list["RepoMember"]] = relationship(
        back_populates="repo", cascade="all, delete-orphan"
    )


class RepoMember(Base):
    """Per-repo role grant: which user has which role on which repo.

    This is the RBAC join table from FULL_STACK_GAP_PLAN.md Phase 2 — it lets
    multiple users share a repo with distinct privilege levels (owner/member/
    viewer) rather than the single-owner model that ``Repo.user_id`` alone gives.
    """

    __tablename__ = "repo_members"
    __table_args__ = (UniqueConstraint("repo_id", "user_id", name="uq_repo_member"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    repo_id: Mapped[str] = mapped_column(
        ForeignKey("repos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), default=ROLE_VIEWER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    repo: Mapped["Repo"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class Conversation(Base):
    """A multi-turn Q&A session (Phase 4). Keyed by user (nullable for anonymous
    dev-mode sessions); messages hang off it in order."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    # Integer autoincrement PK gives a monotonic, gap-free ordering key — message
    # order can't rely on created_at alone (coarse OS clock resolution lets quick
    # successive inserts share a timestamp).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Notification(Base):
    """In-app notification (Phase 3). Durable + cross-process: the worker writes
    a row on job completion and the API serves it over REST and pushes it over
    WebSocket. ``read`` tracks whether the user has seen it."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    type: Mapped[str] = mapped_column(String(32), default="job", nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)


class LlmSetting(Base):
    """App-wide LLM provider configuration (plan Phase C).

    Single-row table keyed by a fixed id (``default``). The API key is stored
    *encrypted* at rest (see ``llm/secretbox.py``) — never in plaintext, and
    never returned over the API. When no row exists the app falls back to the
    ``LLM_*`` environment variables, so this is purely an override layer."""

    __tablename__ = "llm_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    provider: Mapped[str] = mapped_column(String(32), default="ollama", nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Comment(Base):
    """Collaboration (Phase 5): threaded discussion on nodes, risks, etc."""

    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User | None"] = relationship()
