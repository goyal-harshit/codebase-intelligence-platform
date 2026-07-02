"""FastAPI-Users wiring: user manager, JWT auth backend, route dependencies.

Email/password + JWT here; GitHub OAuth lives in ``auth.oauth_github`` and
issues the same JWTs via :func:`get_jwt_strategy`.
The JWT secret comes from ``AUTH_SECRET`` — main.py warns if it is left at the
insecure dev default.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from db import User, get_async_session

DEV_SECRET = "dev-insecure-change-me"
AUTH_SECRET = os.getenv("AUTH_SECRET", DEV_SECRET)
JWT_LIFETIME_SECONDS = int(os.getenv("AUTH_JWT_LIFETIME", "3600"))


async def get_user_db(session=Depends(get_async_session)) -> AsyncGenerator:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(BaseUserManager[User, str]):
    reset_password_token_secret = AUTH_SECRET
    verification_token_secret = AUTH_SECRET

    # IDs are string UUIDs (not native uuid.UUID), so identity-parse them.
    def parse_id(self, value) -> str:
        return str(value)


async def get_user_manager(user_db=Depends(get_user_db)) -> AsyncGenerator:
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=AUTH_SECRET, lifetime_seconds=JWT_LIFETIME_SECONDS)


auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, str](get_user_manager, [auth_backend])

# Reusable dependency for routes that should require a logged-in user.
current_active_user = fastapi_users.current_user(active=True)
