"""Password hashing, JWT creation/validation."""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserApiTokenRow, UserRow
from compliance_os.web.models.database import get_session

JWT_SECRET = os.environ.get("JWT_SECRET", "guardian-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30
OPENCLAW_TOKEN_PREFIX = "gdn_oc"
OPENCLAW_TOKEN_SCOPE = "openclaw"
OPENCLAW_TOKEN_LABEL = "OpenClaw"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "auth_type": "jwt",
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        payload.setdefault("auth_type", "jwt")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def _api_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_openclaw_token(token: str) -> bool:
    return token.startswith(f"{OPENCLAW_TOKEN_PREFIX}_")


def _parse_openclaw_token(token: str) -> tuple[str, str]:
    try:
        _, _, prefix, secret = token.split("_", 3)
    except ValueError as exc:
        raise HTTPException(401, "Invalid API token") from exc
    if not prefix or not secret:
        raise HTTPException(401, "Invalid API token")
    return prefix, secret


def issue_openclaw_token(user: UserRow, db: Session) -> tuple[UserApiTokenRow, str]:
    now = datetime.now(timezone.utc)
    db.query(UserApiTokenRow).filter(
        UserApiTokenRow.user_id == user.id,
        UserApiTokenRow.token_type == OPENCLAW_TOKEN_SCOPE,
        UserApiTokenRow.revoked_at.is_(None),
    ).update(
        {
            UserApiTokenRow.revoked_at: now,
            UserApiTokenRow.updated_at: now,
        },
        synchronize_session=False,
    )

    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(24)
    raw_token = f"{OPENCLAW_TOKEN_PREFIX}_{prefix}_{secret}"
    row = UserApiTokenRow(
        user_id=user.id,
        token_type=OPENCLAW_TOKEN_SCOPE,
        label=OPENCLAW_TOKEN_LABEL,
        scope=OPENCLAW_TOKEN_SCOPE,
        token_prefix=prefix,
        token_hash=_api_token_hash(raw_token),
    )
    db.add(row)
    db.flush()
    return row, raw_token


def get_active_openclaw_token(user_id: str, db: Session) -> UserApiTokenRow | None:
    return (
        db.query(UserApiTokenRow)
        .filter(
            UserApiTokenRow.user_id == user_id,
            UserApiTokenRow.token_type == OPENCLAW_TOKEN_SCOPE,
            UserApiTokenRow.revoked_at.is_(None),
        )
        .order_by(UserApiTokenRow.created_at.desc())
        .first()
    )


def authenticate_api_token(token: str, db: Session) -> dict:
    prefix, _ = _parse_openclaw_token(token)
    row = (
        db.query(UserApiTokenRow)
        .filter(
            UserApiTokenRow.token_prefix == prefix,
            UserApiTokenRow.revoked_at.is_(None),
        )
        .first()
    )
    if not row or not secrets.compare_digest(row.token_hash, _api_token_hash(token)):
        raise HTTPException(401, "Invalid API token")

    user = db.query(UserRow).filter(UserRow.id == row.user_id).first()
    if not user:
        raise HTTPException(401, "User not found")

    now = datetime.now(timezone.utc)
    row.last_used_at = now
    row.updated_at = now
    db.flush()
    return {
        "user_id": user.id,
        "email": user.email,
        "auth_type": "api_token",
        "scope": row.scope,
        "token_type": row.token_type,
        "token_id": row.id,
    }


def decode_token(token: str, db: Session | None = None) -> dict:
    if _is_openclaw_token(token):
        if db is None:
            raise HTTPException(500, "Database session required for API token auth")
        return authenticate_api_token(token, db)
    return decode_jwt_token(token)


def get_bearer_payload(authorization: str | None, db: Session) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    token = authorization.split(" ", 1)[1]
    return decode_token(token, db)


def get_current_user(
    db: Session = Depends(get_session),
    token: str = Depends(lambda: None),  # placeholder, overridden below
) -> UserRow:
    """FastAPI dependency — extracts user from Authorization header."""
    raise HTTPException(401, "Not implemented — use get_current_user_from_header")


def get_current_user_from_header(authorization: str | None = None, db: Session = Depends(get_session)) -> UserRow:
    """Extract user from Authorization: Bearer <token> header."""
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user
