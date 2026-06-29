"""Pydantic schemas for the auth/user API (FastAPI-Users)."""
from __future__ import annotations

from fastapi_users import schemas


class UserRead(schemas.BaseUser[str]):
    full_name: str | None = None


class UserCreate(schemas.BaseUserCreate):
    full_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    full_name: str | None = None
