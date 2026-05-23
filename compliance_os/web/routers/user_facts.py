"""User-facts SoT endpoints.

Per docs/architecture/context-management.md §11, exposes the four core
operations: list active facts, read fact history, lock a user-decided
value, resolve a detected conflict.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.services.auth_service import get_bearer_payload
from compliance_os.web.services.user_facts import (
    get_active_facts,
    get_fact_history,
    resolve_conflict,
    upsert_fact,
)

router = APIRouter(prefix="/api/facts", tags=["user-facts"])


def _get_user(authorization: str | None = Header(None), db: Session = Depends(get_session)) -> UserRow:
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _serialize(row) -> dict:
    return {
        "id": row.id,
        "fact_key": row.fact_key,
        "label": row.label,
        "category": row.category,
        "track": row.track,
        "value": row.value,
        "notes": row.notes,
        "source_type": row.source_type,
        "source_ref": row.source_ref,
        "locked_at": row.locked_at.isoformat() if row.locked_at else None,
        "is_active": row.is_active,
        "superseded_by_id": row.superseded_by_id,
        "detected_conflicts": row.detected_conflicts or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class UpsertFactRequest(BaseModel):
    fact_key: str = Field(..., min_length=1, max_length=128)
    value: Any
    notes: str | None = None
    label: str | None = None


class ResolveConflictRequest(BaseModel):
    choice: str = Field(..., pattern="^(use_new|keep_current|user_value)$")
    user_value: Any = None


@router.get("")
def list_facts(
    category: str | None = None,
    track: str | None = None,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
) -> dict:
    rows = get_active_facts(db, user_id=user.id, category=category, track=track)
    return {"facts": [_serialize(r) for r in rows]}


@router.get("/{fact_key}/history")
def fact_history(
    fact_key: str,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
) -> dict:
    rows = get_fact_history(db, user_id=user.id, fact_key=fact_key)
    return {"history": [_serialize(r) for r in rows]}


@router.post("")
def upsert(
    req: UpsertFactRequest,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
) -> dict:
    new_row, superseded = upsert_fact(
        db,
        user_id=user.id,
        fact_key=req.fact_key,
        value=req.value,
        source_type="user_input",
        source_ref={"ui_path": "/dashboard/facts"},
        notes=req.notes,
        label=req.label,
    )
    db.commit()
    return {
        "fact": _serialize(new_row),
        "superseded": _serialize(superseded) if superseded else None,
    }


@router.post("/{fact_id}/resolve")
def resolve(
    fact_id: str,
    req: ResolveConflictRequest,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
) -> dict:
    try:
        row = resolve_conflict(
            db,
            user_id=user.id,
            fact_id=fact_id,
            choice=req.choice,
            user_value=req.user_value,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    return {"fact": _serialize(row)}
