from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from observability import QUERY_LATENCY

from .audit import record_audit
from .deps import get_query_engine
from .ratelimit import QUERY_LIMIT, limiter
from .security import Principal, get_principal

router = APIRouter()


def _load_history(session_id: str, principal: Principal):
    """Return (history_block, ok). ``ok`` is False if the session exists but the
    caller doesn't own it (a logged-in user querying someone else's session)."""
    from conversations import format_history, get_conversation, recent_messages

    convo = get_conversation(session_id)
    if convo is None:
        return "", True  # unknown id -> treat as a fresh session
    owner = convo.get("user_id")
    if owner is not None and principal.user_id is not None and owner != principal.user_id:
        return "", False
    return format_history(recent_messages(session_id)), True


@router.get("/query")
@limiter.limit(QUERY_LIMIT)
def query(
    request: Request,
    q: str = Query(..., min_length=1, description="natural-language question"),
    top_k: int = 10,
    session_id: Optional[str] = Query(None, description="conversation id for multi-turn"),
    engine=Depends(get_query_engine),
    principal: Principal = Depends(get_principal),
):
    record_audit("query", user_id=principal.user_id, target=q[:512], request=request)
    history = ""
    if session_id:
        history, ok = _load_history(session_id, principal)
        if not ok:
            raise HTTPException(403, "you do not have access to this conversation")
    try:
        with QUERY_LATENCY.time():
            result = engine.answer(q, top_k=top_k, history=history)
    except Exception as e:
        raise HTTPException(503, f"query backend unavailable: {e}")
    # Persist the turn so the next question in this session has memory.
    if session_id:
        from conversations import add_message

        add_message(session_id, "user", q)
        add_message(session_id, "assistant", result.get("answer", ""))
    return result
