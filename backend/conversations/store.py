"""Durable multi-turn conversation storage (Phase 4).

Conversations + their messages live in Postgres/SQLite so a Q&A session has
memory across requests. ``format_history`` renders recent turns into the block
the answer prompt expects.
"""
from __future__ import annotations

from typing import Optional

import db as _db
from db import Conversation, ConversationMessage

# How many trailing messages to feed back into the next answer prompt. Bounds the
# prompt size regardless of how long the conversation grows.
DEFAULT_HISTORY_TURNS = 10


def create_conversation(user_id: Optional[str], title: Optional[str] = None) -> dict:
    with _db.get_sessionmaker()() as s:
        c = Conversation(user_id=user_id, title=title)
        s.add(c)
        s.commit()
        return _conv_dict(c)


def get_conversation(conversation_id: str) -> Optional[dict]:
    with _db.get_sessionmaker()() as s:
        c = s.get(Conversation, conversation_id)
        return _conv_dict(c) if c else None


def list_conversations(user_id: str, limit: int = 50) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        rows = (
            s.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_conv_dict(c) for c in rows]


def add_message(conversation_id: str, role: str, content: str) -> dict:
    with _db.get_sessionmaker()() as s:
        m = ConversationMessage(conversation_id=conversation_id, role=role, content=content)
        s.add(m)
        s.commit()
        return _msg_dict(m)


def get_messages(conversation_id: str, limit: int = 200) -> list[dict]:
    with _db.get_sessionmaker()() as s:
        rows = (
            s.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.id.asc())
            .limit(limit)
            .all()
        )
        return [_msg_dict(m) for m in rows]


def recent_messages(conversation_id: str, turns: int = DEFAULT_HISTORY_TURNS) -> list[dict]:
    """The last ``turns`` messages, oldest-first (for prompt history)."""
    with _db.get_sessionmaker()() as s:
        rows = (
            s.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.id.desc())
            .limit(turns)
            .all()
        )
        return [_msg_dict(m) for m in reversed(rows)]


def format_history(messages: list[dict]) -> str:
    """Render messages into the ``{history}`` block of the answer prompt. Empty
    string when there is nothing yet, so the prompt stays clean for turn one."""
    if not messages:
        return ""
    lines = []
    for m in messages:
        who = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{who}: {m['content']}")
    return "Conversation so far:\n" + "\n".join(lines) + "\n\n"


def _conv_dict(c: Conversation) -> dict:
    return {"id": c.id, "user_id": c.user_id, "title": c.title, "created_at": c.created_at}


def _msg_dict(m: ConversationMessage) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
