"""User-scoped views — what's mine across the whole product.

Sibling to the per-case routers in cases.py. Endpoints here aggregate
across all of a user's cases for the dashboard's "what's the latest"
panels (searches, engagements, etc.). All endpoints require auth.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables import (
    CaseRow,
    EmailThreadRow,
    LawyerEngagementRow,
)
from compliance_os.web.services.auth_service import get_bearer_payload

# How long after outreach we start nudging a follow-up. Lawyers are
# typically slow but not THAT slow — a week without any signal is when
# most users would think "should I bump them?".
FOLLOW_UP_THRESHOLD = timedelta(days=7)
# How recent an inbound thread has to be to count as "new reply" — the
# attention badge is for "since you last looked", and we don't track
# per-user seen state yet, so 7d is the heuristic window.
NEW_REPLY_WINDOW = timedelta(days=7)


# Priority order: lower number = sorted higher (more attention-worthy).
_ATTENTION_PRIORITY = {
    "new_reply": 0,
    "needs_followup": 1,
    "awaiting_response": 2,
    None: 3,
}

router = APIRouter(prefix="/api/me", tags=["me"])


class MyEngagementResponse(BaseModel):
    id: str
    case_id: str
    case_workflow_type: str
    case_status: str
    firm_name: str
    firm_lead_attorney: str | None
    status: str
    notes: str | None
    last_activity_at: str
    thread_count: int
    last_thread_at: str | None
    last_thread_direction: str | None  # "inbound" | "outbound" | None
    last_thread_subject: str | None
    # Computed signal for the dashboard:
    #   "new_reply"        — inbound thread arrived in the last 7 days
    #   "needs_followup"   — outreach_sent + no inbound + 7+ days since activity
    #   "awaiting_response"— outreach_sent + waiting for first reply
    #   null               — engaged / declined / not_contacted / in_discussion
    # Used by the frontend for the attention badge and sort priority.
    attention_label: str | None = None


def _compute_attention(
    *,
    status: str,
    last_thread_at: datetime | None,
    last_thread_direction: str | None,
    last_activity_at: datetime | None,
    now: datetime,
) -> str | None:
    """Derive what the user should look at, if anything.

    Soft heuristics — we never raise priority for engaged/declined
    (the user has already made the call) and never demote in_discussion
    (the user is actively working those).
    """
    if status in ("engaged", "declined"):
        return None

    # Recent inbound = something to read.
    if (
        last_thread_at is not None
        and last_thread_direction == "inbound"
        and (now - last_thread_at) <= NEW_REPLY_WINDOW
    ):
        return "new_reply"

    if status == "outreach_sent":
        # If we've sent outreach but never heard back AND it's been a
        # while, nudge follow-up. Otherwise it's just "awaiting".
        no_inbound = (
            last_thread_at is None or last_thread_direction != "inbound"
        )
        stale = (
            last_activity_at is not None
            and (now - last_activity_at) > FOLLOW_UP_THRESHOLD
        )
        if no_inbound and stale:
            return "needs_followup"
        return "awaiting_response"

    return None


@router.get("/engagements", response_model=list[MyEngagementResponse])
def list_my_engagements(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """List every engagement across the user's cases, newest activity first.

    The dashboard renders this as a flat list with case labels — flat is
    easier to scan than grouped when most users have 1–3 cases.

    Includes denormalized thread metadata (count + last thread direction
    + subject) so the panel renders without N+1 follow-up requests.
    """
    payload = get_bearer_payload(authorization, db)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Authentication required")
    user_id = payload["user_id"]

    # Subquery: per-engagement thread aggregates. LEFT JOIN so engagements
    # without any threads still appear (with thread_count = 0).
    thread_count_sq = (
        db.query(
            EmailThreadRow.engagement_id.label("eid"),
            func.count(EmailThreadRow.id).label("cnt"),
            func.max(EmailThreadRow.last_message_at).label("last_at"),
        )
        .group_by(EmailThreadRow.engagement_id)
        .subquery()
    )

    rows = (
        db.query(
            LawyerEngagementRow,
            CaseRow,
            thread_count_sq.c.cnt,
            thread_count_sq.c.last_at,
        )
        .join(CaseRow, LawyerEngagementRow.case_id == CaseRow.id)
        .outerjoin(
            thread_count_sq,
            thread_count_sq.c.eid == LawyerEngagementRow.id,
        )
        .filter(CaseRow.user_id == user_id)
        .order_by(desc(LawyerEngagementRow.last_activity_at))
        .limit(100)
        .all()
    )

    out: list[MyEngagementResponse] = []
    now = datetime.utcnow()
    for engagement, case, thread_count, last_at in rows:
        # Look up the actual last-thread metadata only if we have one;
        # cheap second query rather than another JOIN.
        last_subj: str | None = None
        last_dir: str | None = None
        if thread_count and thread_count > 0:
            last_thread = (
                db.query(EmailThreadRow)
                .filter(EmailThreadRow.engagement_id == engagement.id)
                .order_by(EmailThreadRow.last_message_at.desc())
                .first()
            )
            if last_thread is not None:
                last_subj = last_thread.subject
                last_dir = last_thread.last_message_direction

        attention = _compute_attention(
            status=engagement.status,
            last_thread_at=last_at,
            last_thread_direction=last_dir,
            last_activity_at=engagement.last_activity_at,
            now=now,
        )

        out.append(MyEngagementResponse(
            id=engagement.id,
            case_id=engagement.case_id,
            case_workflow_type=case.workflow_type or "",
            case_status=case.status or "",
            firm_name=engagement.firm_name,
            firm_lead_attorney=engagement.firm_lead_attorney,
            status=engagement.status,
            notes=engagement.notes,
            last_activity_at=(
                engagement.last_activity_at.isoformat()
                if engagement.last_activity_at
                else ""
            ),
            thread_count=int(thread_count or 0),
            last_thread_at=last_at.isoformat() if last_at else None,
            last_thread_direction=last_dir,
            last_thread_subject=last_subj,
            attention_label=attention,
        ))

    # Re-sort: attention priority first, then last_activity desc within
    # each bucket. The DB query already ordered by last_activity, so this
    # sort is stable within each attention group.
    out.sort(
        key=lambda r: (
            _ATTENTION_PRIORITY.get(r.attention_label, 3),
            -(_iso_to_epoch(r.last_activity_at)),
        )
    )
    return out


def _iso_to_epoch(iso: str) -> float:
    if not iso:
        return 0
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return 0


class ActivityContextResponse(BaseModel):
    text: str


@router.get("/activity-context", response_model=ActivityContextResponse)
def get_activity_context(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Return the user's lawyer-search / engagement / email-thread summary
    as a plain text block, ready to inline into a system prompt.

    Used by the voice agent at call-start so the assistant has the same
    cross-feature awareness the chat assistant gets server-side. Empty
    string when there's nothing to report — caller should still concat
    safely (no special-case needed).
    """
    payload = get_bearer_payload(authorization, db)
    if not payload or "user_id" not in payload:
        raise HTTPException(401, "Authentication required")
    # Imported here to avoid a circular: activity_context imports
    # _compute_attention from this module.
    from compliance_os.web.services.activity_context import build_activity_context
    return ActivityContextResponse(text=build_activity_context(payload["user_id"], db))
