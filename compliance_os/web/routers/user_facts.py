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
from compliance_os.web.services.llm_runtime import chat_completion
from compliance_os.web.services.timeline_builder import build_timeline
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


def _fact_value(value: Any) -> str:
    if isinstance(value, dict) and "v" in value:
        return _fact_value(value.get("v"))
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_fact_value(item) for item in value if _fact_value(item))
    if isinstance(value, dict):
        parts = [f"{key}: {_fact_value(item)}" for key, item in value.items() if _fact_value(item)]
        return "; ".join(parts)
    return str(value)


def _fallback_summary(facts: list, timeline: dict) -> str:
    fact_lines = [
        f"{row.label}: {_fact_value(row.value)}"
        for row in facts
        if _fact_value(row.value)
    ][:6]
    conflicts = sum(len(row.detected_conflicts or []) for row in facts)
    deadlines = sorted(timeline.get("deadlines") or [], key=lambda item: item.get("days", 999))[:2]
    issues = (timeline.get("integrity_issues") or [])[:2]

    parts = []
    if fact_lines:
        parts.append("Guardian sees these current facts: " + "; ".join(fact_lines) + ".")
    else:
        parts.append("Guardian does not have enough locked facts yet; upload documents or answer the next question to build the profile.")
    if deadlines:
        deadline_text = "; ".join(
            f"{item.get('title')} on {item.get('date')} ({item.get('days')} days)"
            for item in deadlines
        )
        parts.append(f"Next timing item: {deadline_text}.")
    if conflicts:
        parts.append(f"{conflicts} fact conflict needs a user decision before Guardian treats the profile as settled.")
    elif issues:
        parts.append(f"Most useful next check: {issues[0].get('title')}.")
    return " ".join(parts)


def _summary_context(facts: list, timeline: dict) -> str:
    rows = [
        f"- {row.label}: {_fact_value(row.value)} "
        f"(category={row.category or 'unknown'}, source={row.source_type}, conflicts={len(row.detected_conflicts or [])})"
        for row in facts
    ]
    deadlines = [
        f"- {item.get('title')}: {item.get('date')} ({item.get('days')} days)"
        for item in (timeline.get("deadlines") or [])[:5]
    ]
    issues = [
        f"- {item.get('title')}: {item.get('message')}"
        for item in (timeline.get("integrity_issues") or [])[:5]
    ]
    return "\n".join([
        "User facts:",
        *(rows or ["- none"]),
        "",
        "Upcoming deadlines:",
        *(deadlines or ["- none"]),
        "",
        "Open data questions:",
        *(issues or ["- none"]),
    ])


@router.get("/summary")
def facts_summary(
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
) -> dict:
    rows = get_active_facts(db, user_id=user.id)
    timeline = build_timeline(user.id, db)
    fallback = _fallback_summary(rows, timeline)
    context = _summary_context(rows, timeline)

    try:
        summary = chat_completion(
            system_prompt=(
                "You are Guardian. Write a concise current-state summary for the user's dashboard. "
                "Use natural prose, no table, no legal advice, and at most one short follow-up question. "
                "Treat user_facts rows as the structured source of truth."
            ),
            messages=[{
                "role": "user",
                "content": (
                    "Summarize the current compliance state from this context in 3-5 sentences. "
                    "Mention the most relevant facts, any unresolved conflict, and the next useful action.\n\n"
                    f"{context}"
                ),
            }],
            temperature=0.2,
            max_tokens=360,
            usage_context={
                "db_session": db,
                "operation": "facts_summary",
                "user_id": user.id,
                "request_metadata": {"fact_count": len(rows)},
            },
        ).strip()
        db.commit()
        return {"summary": summary or fallback, "generated_by": "llm"}
    except Exception:
        db.commit()
        return {"summary": fallback, "generated_by": "local"}


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
        source_type="decision_lock",
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
