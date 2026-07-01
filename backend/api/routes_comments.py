"""Collaboration (Phase 5): threaded comments on risks and graph nodes.
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import db as _db
from auth import current_active_user
from db import Comment, ROLE_OWNER

from .audit import record_audit

router = APIRouter()


class CommentCreate(BaseModel):
    target_type: str = Field(description="Type of entity being commented on, e.g., 'node' or 'risk'")
    target_id: str = Field(description="ID of the target entity")
    body: str = Field(description="Comment body (supports markdown)")


class CommentOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    target_type: str
    target_id: str
    body: str
    created_at: datetime
    updated_at: datetime


@router.get("/comments", response_model=list[CommentOut])
def list_comments(target_type: str, target_id: str):
    """List comments for a specific target."""
    with _db.get_sessionmaker()() as s:
        comments = (
            s.query(Comment)
            .filter(Comment.target_type == target_type, Comment.target_id == target_id)
            .order_by(Comment.created_at.asc())
            .all()
        )
        return comments


@router.post("/comments", response_model=CommentOut, status_code=201)
def create_comment(body: CommentCreate, request: Request, user=Depends(current_active_user)):
    """Add a new comment to a target."""
    with _db.get_sessionmaker()() as s:
        comment = Comment(
            user_id=user.id,
            target_type=body.target_type,
            target_id=body.target_id,
            body=body.body,
        )
        s.add(comment)
        s.commit()
        s.refresh(comment)
        
    record_audit(
        "comment.create",
        user_id=user.id,
        target=f"{body.target_type}:{body.target_id}",
        request=request,
    )
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: str, request: Request, user=Depends(current_active_user)):
    """Delete a comment (must be the author)."""
    with _db.get_sessionmaker()() as s:
        comment = s.get(Comment, comment_id)
        if not comment:
            raise HTTPException(404, "Comment not found")
            
        if comment.user_id != user.id and not user.is_superuser:
            raise HTTPException(403, "Not authorized to delete this comment")
            
        s.delete(comment)
        s.commit()
        
    record_audit(
        "comment.delete",
        user_id=user.id,
        target=f"comment:{comment_id}",
        request=request,
    )
