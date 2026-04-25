"""User-scoped views — what's mine across the whole product.

Sibling to the per-case routers in cases.py. Endpoints here aggregate
across all of a user's cases for the dashboard's "what's the latest"
panels (searches, engagements, etc.). All endpoints require auth.
"""
from __future__ import annotations

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
        ))
    return out
