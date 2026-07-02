# ADR 0005: FastAPI-Users for auth (integrate, don't reinvent)

## Status

Accepted (v1.0, shipped). `PROJECT_PLAN.md` §6 explicitly lists "custom auth" under
**Not building**.

## Context

The platform needs registration, login, password hashing, JWT issuance/validation, and
user management — none of which is differentiating work, and all of which is easy to get
subtly wrong. FastAPI-Users provides audited implementations of exactly this, natively
integrated with FastAPI dependencies and SQLAlchemy.

## Decision

Use FastAPI-Users (`backend/auth/users.py`) for registration (`/auth/register`), JWT
login (`/auth/jwt/login`), and user routes (`/users`), with bcrypt password hashing and
`AUTH_SECRET`-signed tokens. Build the thin project-specific layers on top rather than
replacing the core:

- GitHub OAuth (`backend/auth/oauth_github.py`) reuses FastAPI-Users' JWT strategy and
  its `generate_jwt`/`decode_jwt` helpers for the signed OAuth state token.
- Per-user API keys (`backend/auth/apikeys.py`) hashed in the DB, presented via
  `X-API-Key`.
- A unified `Principal` resolver (`backend/api/security.py`) accepts JWT, static service
  key, or per-user key on every `/api/v1` data route.
- Per-repo RBAC (`backend/auth/rbac.py`) as a dependency factory
  (`require_repo_role`), layered on `current_active_user`.

## Consequences

- Registration, token handling, and password storage follow a maintained upstream
  library; the custom surface area is small and testable.
- The WebSocket endpoint and OAuth callback can mint/verify the same JWTs the HTTP
  routes use (`decode_jwt(token, AUTH_SECRET, ["fastapi-users:auth"])` in
  `backend/main.py`).
- Trade-off: coupled to FastAPI-Users' schema and upgrade cadence; the `User` model
  carries its required columns plus `oauth_provider`/`oauth_subject`.
