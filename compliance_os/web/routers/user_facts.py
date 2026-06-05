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
    serialize_fact,
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
    return serialize_fact(row)


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
    """Brief-report style summary for when the LLM call isn't available.

    Reads like a one-paragraph status briefing — current immigration
    status + employer + the single most-urgent deadline + any open
    decision. Avoids dumping the whole fact table; the SoT panel in
    the UI already shows that.
    """
    if not facts and not timeline.get("deadlines") and not timeline.get("integrity_issues"):
        return (
            "Not enough information yet to brief you on your compliance "
            "state. Upload a document or answer Guardian's next question "
            "to get started."
        )

    by_key = {row.fact_key: _fact_value(row.value).rstrip(".") for row in facts}

    # Headline: current status + how long it's good for.
    headline: str | None = None
    status = by_key.get("current_immigration_status")
    end_date = (
        by_key.get("current_status_end_date")
        or by_key.get("h1b_classification_end_date")
        or by_key.get("stem_opt_end_date")
        or by_key.get("i20_program_end_date")
    )
    if status and end_date:
        headline = f"You're on {status} through {end_date}."
    elif status:
        headline = f"You're on {status}."
    elif end_date:
        headline = f"Your current authorization runs through {end_date}."

    # Employment line.
    employment: str | None = None
    employer = by_key.get("current_employer_legal_name")
    title = by_key.get("current_position_title")
    if employer and title:
        employment = f"Employed as {title} at {employer}."
    elif employer:
        employment = f"Employer of record is {employer}."

    # Entity (for entrepreneur track).
    entity_line: str | None = None
    entity = by_key.get("entity_legal_name")
    if entity:
        ein = by_key.get("entity_ein")
        entity_line = (
            f"Entity on file: {entity} (EIN {ein})." if ein else f"Entity on file: {entity}."
        )

    # Next deadline.
    deadlines = sorted(
        timeline.get("deadlines") or [],
        key=lambda item: item.get("days", 999),
    )
    deadline_line: str | None = None
    if deadlines:
        d = deadlines[0]
        days = d.get("days")
        if isinstance(days, (int, float)) and days <= 30:
            urgency = "Most urgent"
        elif isinstance(days, (int, float)) and days <= 90:
            urgency = "Next deadline"
        else:
            urgency = "Upcoming"
        title_text = d.get("title") or "deadline"
        date_text = d.get("date")
        deadline_line = (
            f"{urgency}: {title_text} on {date_text}"
            + (f" ({int(days)} days out)." if isinstance(days, (int, float)) else ".")
        )

    # Open decision / data quality flag.
    conflicts = sum(len(row.detected_conflicts or []) for row in facts)
    decision_line: str | None = None
    if conflicts:
        n = conflicts
        decision_line = (
            f"{n} fact{'s' if n != 1 else ''} need{'' if n != 1 else 's'} "
            "a quick decision in the conflicts panel before Guardian "
            "treats the profile as settled."
        )
    else:
        issues = (timeline.get("integrity_issues") or [])[:1]
        if issues:
            decision_line = f"Useful next check: {issues[0].get('title')}."

    return " ".join(
        part for part in (headline, employment, entity_line, deadline_line, decision_line)
        if part
    ) or "Profile state is partial — upload a document to fill it in."


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
                "You are Guardian. Write a brief executive-style status report "
                "for the user's compliance dashboard — like the opening "
                "paragraph of an attorney briefing memo, not a fact list. "
                "Lead with the current immigration status and how long it's "
                "valid. Mention the employer / entity / role only if it's "
                "relevant context. Call out the single most urgent deadline. "
                "Flag any unresolved conflict as a decision needed. End with "
                "one concrete next action. Plain prose only, no bullets, no "
                "headers, no tables. 3-5 short sentences. No legal advice "
                "framing — just the operational state."
            ),
            messages=[{
                "role": "user",
                "content": (
                    "Brief me on my current compliance state from this "
                    "context. Treat user_facts as the source of truth; "
                    "ignore anything that contradicts them.\n\n"
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
