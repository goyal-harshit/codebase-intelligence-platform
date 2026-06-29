"""Authentication layer (FastAPI-Users: email/password + JWT)."""
from .schemas import UserCreate, UserRead, UserUpdate
from .users import auth_backend, current_active_user, fastapi_users

__all__ = [
    "auth_backend",
    "current_active_user",
    "fastapi_users",
    "UserCreate",
    "UserRead",
    "UserUpdate",
]
