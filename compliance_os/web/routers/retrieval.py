"""Version-aware retrieval context endpoints for uploaded documents."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow
from compliance_os.web.services.retrieval import build_check_retrieval_context

router = APIRouter(prefix="/api/checks/{check_id}", tags=["retrieval"])


@router.get("/retrieval-context")
def get_retrieval_context(
    check_id: str,
    query: str | None = Query(None),
    db: Session = Depends(get_session),
):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return build_check_retrieval_context(check, query=query)
