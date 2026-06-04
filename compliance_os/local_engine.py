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
from compliance_os.web.services.user_facts import (
    get_active_facts,
    resolve_conflict,
    serialize_fact,
    upsert_fact,
)

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


def local_get_facts(category: str = "", track: str = "") -> dict:
    """In-process equivalent of GET /api/facts → {"facts": [...]}."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        rows = get_active_facts(
            db, user_id=user_id,
            category=category or None, track=track or None,
        )
        return {"facts": [serialize_fact(r) for r in rows]}
    finally:
        db.close()


def local_set_fact(
    fact_key: str, value, notes: str = "", label: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts (a user-locked decision)."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        new_row, superseded = upsert_fact(
            db, user_id=user_id, fact_key=fact_key, value=value,
            source_type="decision_lock",
            source_ref={"ui_path": "mcp:set_user_fact"},
            notes=notes or None, label=label or None,
        )
        db.commit()
        return {
            "fact": serialize_fact(new_row),
            "superseded": serialize_fact(superseded) if superseded else None,
        }
    finally:
        db.close()


def local_resolve_conflict(
    fact_id: str, choice: str, user_value: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts/{fact_id}/resolve."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        row = resolve_conflict(
            db, user_id=user_id, fact_id=fact_id,
            choice=choice, user_value=user_value or None,
        )
        db.commit()
        return {"fact": serialize_fact(row)}
    finally:
        db.close()


def force_local_embeddings() -> None:
    """Pin embeddings to the local provider so no OpenAI key is ever used
    in local mode (privacy + $0 cost). Idempotent."""
    os.environ["GUARDIAN_EMBEDDING_PROVIDER"] = "local"
