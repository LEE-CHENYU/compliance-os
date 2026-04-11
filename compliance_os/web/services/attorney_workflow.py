"""Helpers for the attorney-backed marketplace workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.models.marketplace import (
    AttorneyAssignmentRow,
    AttorneyRow,
    LimitedScopeAgreementRow,
    MarketplaceUserRow,
    OrderRow,
)
from compliance_os.web.services.pdf_builder import build_text_pdf


ATTORNEY_CHECKLIST_DIR = Path(__file__).resolve().parents[3] / "config" / "attorney_checklists"
AGREEMENT_TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates" / "agreements"
ATTORNEY_ARTIFACT_DIR = DATA_DIR / "marketplace" / "attorney_workflow"
SERVICE_ALIASES = {
    "opt_execution": "opt_execution",
    "opt_advisory": "opt_execution",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_service(service_sku: str) -> str:
    return SERVICE_ALIASES.get(service_sku, service_sku)


def _artifact_dir(order: OrderRow) -> Path:
    path = ATTORNEY_ARTIFACT_DIR / _normalize_service(order.product_sku) / order.id / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _upsert_artifact(
    result_data: dict[str, Any],
    *,
    label: str,
    path: Path,
) -> None:
    existing: list[dict[str, Any]] = []
    for artifact in result_data.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        artifact_filename = Path(str(artifact.get("filename") or artifact.get("path") or "")).name
        if artifact_filename == path.name:
            continue
        existing.append(artifact)
    existing.append(
        {
            "label": label,
            "filename": path.name,
            "path": str(path),
        }
    )
    result_data["artifacts"] = existing


def _build_g28_packet(order: OrderRow, assignment: AttorneyAssignmentRow) -> dict[str, Any]:
    intake = (order.intake_data or {}).get("client_intake") or {}
    documents = intake.get("documents") or []
    supporting_documents = ", ".join(
        str(document.get("doc_type") or "").replace("_", " ")
        for document in documents
        if isinstance(document, dict) and str(document.get("doc_type") or "").strip()
    ) or "No uploaded supporting documents"
    client_name = "Client"
    if order.user is not None:
        client_name = order.user.full_name or order.user.email
    attorney_name = assignment.attorney.full_name if assignment.attorney is not None else "Guardian panel attorney"

    lines = [
        f"Client: {client_name}",
        f"Attorney: {attorney_name}",
        f"Service: {order.product.name if order.product is not None else order.product_sku}",
        "",
        "Execution packet summary",
        f"- Desired OPT start date: {intake.get('desired_start_date') or 'Not provided'}",
        f"- Supporting documents: {supporting_documents}",
        "",
        "Attorney notes",
        assignment.attorney_notes or "Approved for filing.",
    ]
    path = _artifact_dir(order) / "g-28-signature-packet.pdf"
    path.write_bytes(
        build_text_pdf(
            "G-28 Signature Packet",
            lines,
            subtitle="Guardian attorney review",
        )
    )
    return {
        "label": "Download G-28 signature packet",
        "filename": path.name,
        "path": str(path),
    }


def _build_filing_confirmation_packet(
    order: OrderRow,
    *,
    receipt_number: str,
    filing_confirmation: str | None,
    filed_at: str,
) -> dict[str, Any]:
    client_name = "Client"
    if order.user is not None:
        client_name = order.user.full_name or order.user.email
    lines = [
        f"Client: {client_name}",
        f"Service: {order.product.name if order.product is not None else order.product_sku}",
        f"Receipt number: {receipt_number}",
        f"Recorded at: {filed_at}",
        "",
        filing_confirmation or "Guardian recorded the filing confirmation for this case.",
    ]
    path = _artifact_dir(order) / "filing-confirmation.pdf"
    path.write_bytes(
        build_text_pdf(
            "Filing Confirmation",
            lines,
            subtitle="Guardian filing record",
        )
    )
    return {
        "label": "Download filing confirmation",
        "filename": path.name,
        "path": str(path),
    }


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
    result_data = dict(order.result_data or {})
    assignment.checklist_responses = checklist_responses
    assignment.decision = decision
    assignment.attorney_notes = notes
    assignment.reviewed_at = _now()
    assignment.completed_at = _now()
    order.updated_at = _now()

    if decision == "approve":
        order.status = "ready_to_file"
        next_action = "ready_to_file"
        result_data["summary"] = "Attorney review approved your OPT case for filing."
        result_data["next_steps"] = [
            "Guardian prepared the attorney-reviewed filing packet for this order.",
            "The attorney can now submit the case and record the USCIS receipt number here.",
        ]
        result_data["upgrade_offer"] = None
        g28_packet = _build_g28_packet(order, assignment)
        _upsert_artifact(
            result_data,
            label=str(g28_packet["label"]),
            path=Path(str(g28_packet["path"])),
        )
    elif decision == "flag_upgrade":
        order.status = "flagged"
        next_action = "offer_advisory_upgrade"
        result_data["summary"] = "Attorney review flagged this case for Advisory Mode before filing."
        result_data["next_steps"] = [
            "Review the attorney note for the complexity that blocked the execution lane.",
            "Continue into OPT Advisory Mode so the attorney can resolve the strategy issues before filing.",
        ]
        result_data["upgrade_offer"] = {
            "target_sku": "opt_advisory",
            "credit_cents": 19900,
            "reason": notes or "Attorney review identified issues that need advisory handling before filing.",
            "accepted_order_id": None,
        }
    else:
        raise ValueError("Unsupported review decision")

    order.result_data = result_data
    return {"next_action": next_action}


def record_filing(
    order: OrderRow,
    assignment: AttorneyAssignmentRow,
    *,
    receipt_number: str,
    filing_confirmation: str | None,
) -> dict[str, Any]:
    result_data = dict(order.result_data or {})
    filed_at = _now().isoformat()
    result_data.update(
        {
            "summary": filing_confirmation or "OPT application filed.",
            "receipt_number": receipt_number,
            "filing_confirmation": filing_confirmation,
            "filed_at": filed_at,
            "next_steps": [
                "Use the USCIS receipt number to track the case status.",
                "Keep the filing confirmation and attorney packet in your records.",
            ],
        }
    )
    confirmation_packet = _build_filing_confirmation_packet(
        order,
        receipt_number=receipt_number,
        filing_confirmation=filing_confirmation,
        filed_at=filed_at,
    )
    _upsert_artifact(
        result_data,
        label=str(confirmation_packet["label"]),
        path=Path(str(confirmation_packet["path"])),
    )
    order.result_data = result_data
    order.status = "completed"
    order.completed_at = _now()
    order.updated_at = _now()
    assignment.completed_at = _now()
    return result_data
