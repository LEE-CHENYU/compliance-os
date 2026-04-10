"""Attorney portal endpoints for attorney-backed marketplace orders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.marketplace import AttorneyAssignmentRow, AttorneyRow, OrderRow
from compliance_os.web.routers.marketplace import _serialize_order
from compliance_os.web.services.attorney_workflow import (
    latest_agreement,
    latest_assignment,
    load_attorney_checklist,
    record_filing,
    record_review,
    serialize_assignment,
    serialize_attorney,
)
from compliance_os.web.services.auth_service import get_bearer_payload


router = APIRouter(prefix="/api/attorney", tags=["attorney"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewRequest(BaseModel):
    checklist_responses: dict[str, bool]
    decision: str
    notes: str | None = None


class FilingRequest(BaseModel):
    receipt_number: str
    filing_confirmation: str | None = None


class FlagUpgradeRequest(BaseModel):
    flag_reason: str
    notes: str | None = None


def _require_attorney_account(
    authorization: str | None,
    db: Session,
) -> tuple[UserRow, AttorneyRow]:
    payload = get_bearer_payload(authorization, db)
    if payload.get("auth_type") != "jwt":
        raise HTTPException(status_code=403, detail="This endpoint requires a web session token")

    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if user.role not in {"attorney", "admin"}:
        raise HTTPException(status_code=403, detail="Attorney role required")

    attorney = db.query(AttorneyRow).filter(AttorneyRow.email == user.email).first()
    if attorney is None:
        raise HTTPException(status_code=404, detail="Attorney profile not found")
    return user, attorney


def _owned_assignment(order_id: str, attorney: AttorneyRow, db: Session) -> tuple[OrderRow, AttorneyAssignmentRow]:
    assignment = (
        db.query(AttorneyAssignmentRow)
        .filter(
            AttorneyAssignmentRow.order_id == order_id,
            AttorneyAssignmentRow.attorney_id == attorney.id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Case not found")

    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order, assignment


def _serialize_case(order: OrderRow, assignment: AttorneyAssignmentRow) -> dict[str, Any]:
    agreement = latest_agreement(order)
    checklist = load_attorney_checklist(order.product_sku)
    return {
        "order": _serialize_order(order, include_result=True),
        "assignment": serialize_assignment(assignment),
        "agreement": {
            "agreement_id": agreement.id,
            "signed_at": agreement.signed_at.isoformat() if agreement and agreement.signed_at else None,
            "user_signature": agreement.user_signature if agreement else None,
            "agreement_text": agreement.agreement_text if agreement else None,
        } if agreement else None,
        "checklist": checklist,
        "intake_data": order.intake_data or {},
        "result": order.result_data or {},
    }


@router.get("/dashboard")
def get_dashboard(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, attorney = _require_attorney_account(authorization, db)
    assignments = (
        db.query(AttorneyAssignmentRow)
        .filter(AttorneyAssignmentRow.attorney_id == attorney.id)
        .order_by(AttorneyAssignmentRow.assigned_at.desc())
        .all()
    )

    pending_cases: list[dict[str, Any]] = []
    completed_cases: list[dict[str, Any]] = []
    for assignment in assignments:
        order = assignment.order
        entry = {
            "order_id": assignment.order_id,
            "product_sku": order.product_sku if order is not None else None,
            "status": order.status if order is not None else None,
            "decision": assignment.decision,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            "client_email": order.user.email if order is not None and order.user is not None else None,
            "client_name": order.user.full_name if order is not None and order.user is not None else None,
        }
        if assignment.decision == "pending":
            pending_cases.append(entry)
        else:
            completed_cases.append(entry)

    return {
        "attorney": serialize_attorney(attorney),
        "pending_cases": pending_cases,
        "completed_cases": completed_cases,
        "stats": {
            "pending_review": len(pending_cases),
            "completed_reviews": len(completed_cases),
            "total_cases": len(assignments),
        },
    }


@router.get("/cases/{order_id}")
def get_case(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, attorney = _require_attorney_account(authorization, db)
    order, assignment = _owned_assignment(order_id, attorney, db)
    return _serialize_case(order, assignment)


@router.post("/cases/{order_id}/review")
def review_case(
    order_id: str,
    payload: ReviewRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, attorney = _require_attorney_account(authorization, db)
    order, assignment = _owned_assignment(order_id, attorney, db)

    result = record_review(
        order,
        assignment,
        checklist_responses=payload.checklist_responses,
        decision=payload.decision,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(order)
    db.refresh(assignment)
    return {
        "decision_recorded": True,
        "next_action": result["next_action"],
        "assignment": serialize_assignment(assignment),
        "order": _serialize_order(order, include_result=True),
    }


@router.post("/cases/{order_id}/file")
def file_case(
    order_id: str,
    payload: FilingRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, attorney = _require_attorney_account(authorization, db)
    order, assignment = _owned_assignment(order_id, attorney, db)

    if assignment.decision != "approve":
        raise HTTPException(status_code=400, detail="Approve the case before filing it")

    result = record_filing(
        order,
        assignment,
        receipt_number=payload.receipt_number,
        filing_confirmation=payload.filing_confirmation,
    )
    db.commit()
    return {
        "filed_at": result["filed_at"],
        "receipt_number": result["receipt_number"],
        "order": _serialize_order(order, include_result=True),
    }


@router.post("/cases/{order_id}/flag-upgrade")
def flag_upgrade(
    order_id: str,
    payload: FlagUpgradeRequest = Body(...),
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, attorney = _require_attorney_account(authorization, db)
    order, assignment = _owned_assignment(order_id, attorney, db)

    order.status = "flagged"
    order.updated_at = _now()
    assignment.decision = "flag_upgrade"
    assignment.attorney_notes = "\n\n".join(filter(None, [payload.flag_reason, payload.notes]))
    assignment.reviewed_at = _now()
    assignment.completed_at = _now()
    db.commit()
    return {
        "flagged": True,
        "user_notified": False,
        "order": _serialize_order(order, include_result=True),
        "assignment": serialize_assignment(assignment),
    }
