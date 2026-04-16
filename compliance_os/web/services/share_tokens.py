"""Scoped share tokens for external collaborators (lawyers, CPAs).

Tokens are short-lived JWTs embedding a folder path + template id +
optional recipient label. They authorize read-only access to a single
case package — no other Guardian API scope.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from compliance_os.web.services.auth_service import JWT_ALGORITHM, JWT_SECRET

SHARE_TOKEN_SCOPE = "share"
DEFAULT_EXPIRY_DAYS = 14


def create_share_token(
    folder: str,
    template_id: str,
    recipient: str = "",
    expires_in_days: int = DEFAULT_EXPIRY_DAYS,
    issuer: str = "",
) -> str:
    """Issue a read-only share token for a case folder."""
    now = datetime.now(timezone.utc)
    payload = {
        "scope": SHARE_TOKEN_SCOPE,
        "folder": folder,
        "template_id": template_id,
        "recipient": recipient,
        "issuer": issuer,
        "iat": now,
        "exp": now + timedelta(days=expires_in_days),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_share_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(410, "Share link has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid share link")
    if payload.get("scope") != SHARE_TOKEN_SCOPE:
        raise HTTPException(401, "Token scope mismatch")
    return payload
