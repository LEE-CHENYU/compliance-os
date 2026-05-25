"""User-facts SoT service.

Implements the storage rules from docs/architecture/context-management.md
— semi-structured per-user fact rows with provenance, decision-lock,
supersession, and conflict-detection metadata.

Public API:
    upsert_fact(...)        — atomic insert-or-supersede for a (user, fact_key)
    record_conflict(...)    — push a conflict onto an existing active row
    get_active_facts(...)   — return active facts, optionally filtered
    get_fact_history(...)   — full history (active + superseded) for one key
    resolve_conflict(...)   — user-driven conflict resolution
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from compliance_os.facts.vocabulary import resolve_fact_def
from compliance_os.web.models.tables_v2 import UserFactRow


SOURCE_TYPES = {"document", "decision_lock", "gmail", "external_api", "user_input"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _wrap_value(value: Any, **metadata: Any) -> dict:
    """Wrap a raw value in the canonical {"v": ..., ...metadata} envelope.

    Already-wrapped values pass through unchanged so callers don't have
    to special-case re-saves.
    """
    if isinstance(value, dict) and "v" in value:
        return value
    payload: dict[str, Any] = {"v": value}
    payload.update(metadata)
    return payload


def _decision_source_ref(source_ref: dict | None, *, resolution: str) -> dict:
    ref = dict(source_ref or {})
    ref["resolution"] = resolution
    ref["resolved_at"] = _now().isoformat()
    return ref


def upsert_fact(
    db: Session,
    *,
    user_id: str,
    fact_key: str,
    value: Any,
    source_type: str,
    source_ref: dict | None = None,
    notes: str | None = None,
    label: str | None = None,
    locked_at: datetime | None = None,
) -> tuple[UserFactRow, UserFactRow | None]:
    """Insert or supersede the active row for (user_id, fact_key).

    Returns (new_row, superseded_row_or_None). The caller can inspect
    superseded_row to surface "we replaced your previous H-1B end date
    of X with Y, sourced from document Z."

    When an active row exists and:
      - the new value equals the existing one → no-op; returns
        (existing_row, None) and just refreshes locked_at + source_ref.
      - the new value differs → marks the existing row is_active=False,
        sets supersedes_by, and writes a fresh active row.

    Does NOT auto-call record_conflict. Conflicts are recorded by the
    caller (typically the post-upload hook) BEFORE deciding whether to
    supersede.
    """
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type}")

    fd = resolve_fact_def(fact_key)
    final_label = label or (fd.label if fd else fact_key.replace("_", " ").title())
    final_category = fd.category if fd else None
    final_track = fd.track if fd else None
    wrapped = _wrap_value(value)
    now = locked_at or _now()

    existing = (
        db.query(UserFactRow)
        .filter(
            UserFactRow.user_id == user_id,
            UserFactRow.fact_key == fact_key,
            UserFactRow.is_active.is_(True),
        )
        .one_or_none()
    )

    if existing is not None:
        # Same value? Refresh metadata in place; no supersession.
        if existing.value == wrapped:
            existing.locked_at = now
            existing.source_type = source_type
            existing.label = final_label
            existing.category = final_category
            existing.track = final_track
            if source_ref:
                existing.source_ref = source_ref
            if notes is not None:
                existing.notes = notes
            existing.updated_at = now
            db.flush()
            return existing, None

        # Value differs → supersede.
        existing.is_active = False
        existing.updated_at = now
        db.flush()

    new_row = UserFactRow(
        user_id=user_id,
        fact_key=fact_key,
        label=final_label,
        category=final_category,
        track=final_track,
        value=wrapped,
        notes=notes,
        source_type=source_type,
        source_ref=source_ref,
        locked_at=now,
        is_active=True,
        detected_conflicts=[],
    )
    db.add(new_row)
    db.flush()

    if existing is not None:
        existing.superseded_by_id = new_row.id
        db.flush()

    return new_row, existing


def record_conflict(
    db: Session,
    *,
    user_id: str,
    fact_key: str,
    claimed_value: Any,
    source_ref: dict | None,
    detected_at: datetime | None = None,
) -> UserFactRow | None:
    """Append a conflict entry to the active fact row.

    Used by the post-upload hook when a new document's extracted value
    contradicts the active fact AND the new document doesn't clearly
    supersede the fact's current source (different chain, no later
    effective date, etc.). Conflict resolution is then a user action.

    Returns the updated row, or None if no active row exists yet
    (in that case the caller should `upsert_fact` instead — there's
    nothing to conflict with).
    """
    row = (
        db.query(UserFactRow)
        .filter(
            UserFactRow.user_id == user_id,
            UserFactRow.fact_key == fact_key,
            UserFactRow.is_active.is_(True),
        )
        .one_or_none()
    )
    if row is None:
        return None
    conflicts = list(row.detected_conflicts or [])
    conflicts.append({
        "claimed_value": _wrap_value(claimed_value),
        "source_ref": source_ref,
        "detected_at": (detected_at or _now()).isoformat(),
    })
    row.detected_conflicts = conflicts
    row.updated_at = _now()
    db.flush()
    return row


def get_active_facts(
    db: Session,
    *,
    user_id: str,
    category: str | None = None,
    track: str | None = None,
) -> list[UserFactRow]:
    """Active facts for a user, optionally filtered by category/track."""
    q = db.query(UserFactRow).filter(
        UserFactRow.user_id == user_id,
        UserFactRow.is_active.is_(True),
    )
    if category:
        q = q.filter(UserFactRow.category == category)
    if track:
        q = q.filter(UserFactRow.track.in_([track, "shared"]))
    return q.order_by(UserFactRow.category, UserFactRow.label).all()


def get_fact_history(
    db: Session, *, user_id: str, fact_key: str
) -> list[UserFactRow]:
    """All rows (active + superseded) for one fact, newest first."""
    return (
        db.query(UserFactRow)
        .filter(
            UserFactRow.user_id == user_id,
            UserFactRow.fact_key == fact_key,
        )
        .order_by(desc(UserFactRow.locked_at))
        .all()
    )


def resolve_conflict(
    db: Session,
    *,
    user_id: str,
    fact_id: str,
    choice: str,
    user_value: Any = None,
) -> UserFactRow:
    """Apply a user decision to a row's detected_conflicts list.

    `choice` is one of:
      - "use_new":   take the first conflict's claimed_value, supersede.
      - "keep_current": clear conflicts, keep current row.
      - "user_value": supersede with the explicit `user_value`.
    """
    row = (
        db.query(UserFactRow)
        .filter(UserFactRow.id == fact_id, UserFactRow.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        raise ValueError(f"fact {fact_id} not found for user {user_id}")
    conflicts = list(row.detected_conflicts or [])

    if choice == "keep_current":
        row.detected_conflicts = []
        row.source_type = "decision_lock"
        row.source_ref = _decision_source_ref(
            row.source_ref,
            resolution="keep_current",
        )
        row.updated_at = _now()
        db.flush()
        return row

    if choice == "use_new":
        if not conflicts:
            return row
        first = conflicts[0]
        new_row, _ = upsert_fact(
            db,
            user_id=user_id,
            fact_key=row.fact_key,
            value=first["claimed_value"],
            source_type="decision_lock",
            source_ref=_decision_source_ref(
                first.get("source_ref"),
                resolution=f"use_new:{fact_id}",
            ),
        )
        return new_row

    if choice == "user_value":
        new_row, _ = upsert_fact(
            db,
            user_id=user_id,
            fact_key=row.fact_key,
            value=user_value,
            source_type="decision_lock",
            source_ref=_decision_source_ref(
                {"resolved_from": fact_id},
                resolution="user_value",
            ),
        )
        return new_row

    raise ValueError(f"unknown choice: {choice}")
