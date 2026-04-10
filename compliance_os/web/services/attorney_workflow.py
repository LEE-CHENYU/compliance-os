"""Helpers for the attorney-backed marketplace workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from compliance_os.web.models.marketplace import (
    AttorneyAssignmentRow,
    AttorneyRow,
    LimitedScopeAgreementRow,
    MarketplaceUserRow,
    OrderRow,
)


ATTORNEY_CHECKLIST_DIR = Path(__file__).resolve().parents[3] / "config" / "attorney_checklists"
AGREEMENT_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "agreements"
SERVICE_ALIASES = {
    "opt_execution": "opt_execution",
    "opt_advisory": "opt_execution",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_service(service_sku: str) -> str:
    return SERVICE_ALIASES.get(service_sku, service_sku)


@lru_cache(maxsize=8)
def load_attorney_checklist(service_sku: str) -> dict[str, Any]:
    normalized = _normalize_service(service_sku)
    path = ATTORNEY_CHECKLIST_DIR / f"{normalized}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Attorney checklist not found for {service_sku}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid attorney checklist for {service_sku}")
    return data


def select_available_attorney(db: Session) -> AttorneyRow | None:
    return (
        db.query(AttorneyRow)
        .filter(AttorneyRow.active.is_(True))
        .order_by(AttorneyRow.created_at.asc())
        .first()
    )


def latest_assignment(order: OrderRow) -> AttorneyAssignmentRow | None:
    if not order.attorney_assignments:
        return None
    return sorted(order.attorney_assignments, key=lambda item: item.assigned_at or _now())[-1]


def latest_agreement(order: OrderRow) -> LimitedScopeAgreementRow | None:
    if not order.agreements:
        return None
    return sorted(order.agreements, key=lambda item: item.signed_at or _now())[-1]


def serialize_attorney(attorney: AttorneyRow | None) -> dict[str, Any] | None:
    if attorney is None:
        return None
    return {
        "attorney_id": attorney.id,
        "full_name": attorney.full_name,
        "email": attorney.email,
        "bar_state": attorney.bar_state,
        "bar_number": attorney.bar_number,
        "bar_verified": bool(attorney.bar_verified),
        "languages": list(attorney.languages or []),
        "location": attorney.location,
    }


def serialize_assignment(assignment: AttorneyAssignmentRow | None) -> dict[str, Any] | None:
    if assignment is None:
        return None
    return {
        "assignment_id": assignment.id,
        "attorney_id": assignment.attorney_id,
        "decision": assignment.decision,
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        "reviewed_at": assignment.reviewed_at.isoformat() if assignment.reviewed_at else None,
        "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
        "checklist_responses": assignment.checklist_responses or {},
        "attorney_notes": assignment.attorney_notes,
        "attorney": serialize_attorney(assignment.attorney),
    }


def render_limited_scope_agreement(
    order: OrderRow,
    user: MarketplaceUserRow,
    attorney: AttorneyRow | None,
) -> str:
    normalized = _normalize_service(order.product_sku)
    path = AGREEMENT_TEMPLATE_DIR / f"{normalized}_agreement.md"
    if not path.exists():
        raise FileNotFoundError(f"Agreement template not found for {order.product_sku}")
    template = path.read_text(encoding="utf-8")
    return template.format(
        client_name=user.full_name or user.email,
        attorney_name=attorney.full_name if attorney is not None else "Guardian panel attorney",
        bar_number=attorney.bar_number if attorney is not None else "Pending assignment",
        service_name=order.product.name if order.product is not None else order.product_sku,
        agreement_date=_now().date().isoformat(),
    )


def assign_attorney_to_order(order: OrderRow, db: Session) -> AttorneyAssignmentRow:
    existing = latest_assignment(order)
    if existing is not None:
        return existing

    attorney = select_available_attorney(db)
    if attorney is None:
        raise RuntimeError("No active attorney is available")

    assignment = AttorneyAssignmentRow(
        order_id=order.id,
        attorney_id=attorney.id,
        decision="pending",
    )
    db.add(assignment)
    order.status = "attorney_review"
    order.updated_at = _now()
    db.flush()
    return assignment


def record_review(
    order: OrderRow,
    assignment: AttorneyAssignmentRow,
    *,
    checklist_responses: dict[str, Any],
    decision: str,
    notes: str | None,
) -> dict[str, Any]:
    assignment.checklist_responses = checklist_responses
    assignment.decision = decision
    assignment.attorney_notes = notes
    assignment.reviewed_at = _now()
    assignment.completed_at = _now()
    order.updated_at = _now()

    if decision == "approve":
        order.status = "ready_to_file"
        next_action = "ready_to_file"
    elif decision == "flag_upgrade":
        order.status = "flagged"
        next_action = "offer_advisory_upgrade"
    else:
        raise ValueError("Unsupported review decision")

    return {"next_action": next_action}


def record_filing(
    order: OrderRow,
    assignment: AttorneyAssignmentRow,
    *,
    receipt_number: str,
    filing_confirmation: str | None,
) -> dict[str, Any]:
    result_data = dict(order.result_data or {})
    result_data.update(
        {
            "summary": filing_confirmation or "OPT application filed.",
            "receipt_number": receipt_number,
            "filing_confirmation": filing_confirmation,
            "filed_at": _now().isoformat(),
        }
    )
    order.result_data = result_data
    order.status = "completed"
    order.completed_at = _now()
    order.updated_at = _now()
    assignment.completed_at = _now()
    return result_data
