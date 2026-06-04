# compliance_os/local_engine.py
"""In-process local engine for the Guardian MCP extension.

When GUARDIAN_MODE=local, the MCP tools call these adapters instead of
proxying to the hosted Guardian API. Everything runs against the local
SQLite SoT at ~/.guardian/guardian.db using the already transport-
agnostic service layer in compliance_os.web.services.*.
"""
from __future__ import annotations

import os
import secrets

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session

LOCAL_USER_EMAIL = "local@guardian.local"


def is_local_mode() -> bool:
    """True when the extension should run fully in-process (no hosted API)."""
    return (os.environ.get("GUARDIAN_MODE") or "").strip().lower() == "local"


def get_local_user_id(db) -> str:
    """Return the singleton local user's id, creating it on first use.

    Local mode is single-user (whoever installed the extension), so there
    is no auth — we only need a stable user_id to scope SoT rows. The
    password_hash is random and never used for login.
    """
    user = (
        db.query(UserRow)
        .filter(UserRow.email == LOCAL_USER_EMAIL)
        .one_or_none()
    )
    if user is None:
        user = UserRow(
            email=LOCAL_USER_EMAIL,
            password_hash=secrets.token_hex(16),
            role="user",
        )
        db.add(user)
        db.commit()
    return user.id
