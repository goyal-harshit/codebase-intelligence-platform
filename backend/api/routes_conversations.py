"""Conversation management for multi-turn Q&A (Phase 4).

Create a conversation to get a ``session_id``, then pass it to ``GET /query``;
each turn is persisted so later questions have memory. Ownership mirrors the
query route: anonymous (dev-mode) sessions are open; a session owned by a user is
visible only to that user.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from conversations import (
    create_conversation,
    get_conversation,
    get_messages,
    list_conversations,
)

from .security import Principal, get_principal

router = APIRouter()


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationInfo(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: datetime


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


def _require_access(session_id: str, principal: Principal) -> dict:
    convo = get_conversation(session_id)
    if convo is None:
        raise HTTPException(404, "unknown conversation")
    owner = convo.get("user_id")
    if owner is not None and owner != principal.user_id:
        raise HTTPException(403, "you do not have access to this conversation")
    return convo


@router.post("/conversations", response_model=ConversationInfo, status_code=201)
def create_conversation_route(
    body: ConversationCreate, principal: Principal = Depends(get_principal)
):
    return create_conversation(principal.user_id, title=body.title)


@router.get("/conversations", response_model=list[ConversationInfo])
def list_conversations_route(principal: Principal = Depends(get_principal)):
    if principal.user_id is None:
        raise HTTPException(401, "login required to list conversations")
    return list_conversations(principal.user_id)


@router.get("/conversations/{session_id}/messages", response_model=list[MessageInfo])
def get_messages_route(session_id: str, principal: Principal = Depends(get_principal)):
    _require_access(session_id, principal)
    return get_messages(session_id)
