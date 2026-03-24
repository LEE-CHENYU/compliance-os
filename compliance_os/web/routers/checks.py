"""Check session CRUD + answers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas_v2 import Check, CheckCreate, CheckUpdate
from compliance_os.web.models.tables_v2 import CheckRow

router = APIRouter(prefix="/api/checks", tags=["checks"])


@router.post("", response_model=Check)
def create_check(body: CheckCreate, db: Session = Depends(get_session)):
    row = CheckRow(track=body.track, answers=body.answers, stage=body.answers.get("stage"))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{check_id}", response_model=Check)
def get_check(check_id: str, db: Session = Depends(get_session)):
    row = db.get(CheckRow, check_id)
    if not row:
        raise HTTPException(404, "Check not found")
    return row


@router.patch("/{check_id}", response_model=Check)
def update_check(check_id: str, body: CheckUpdate, db: Session = Depends(get_session)):
    row = db.get(CheckRow, check_id)
    if not row:
        raise HTTPException(404, "Check not found")
    if body.answers is not None:
        merged = {**(row.answers or {}), **body.answers}
        row.answers = merged
        row.stage = merged.get("stage", row.stage)
    if body.status is not None:
        row.status = body.status
    db.commit()
    db.refresh(row)
    return row
