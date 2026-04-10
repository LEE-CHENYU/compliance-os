"""Marketplace catalog, order, intake, and result endpoints."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.marketplace import EmailSequenceRow, MarketplaceUserRow, OrderRow, ProductRow
from compliance_os.web.services.auth_service import get_bearer_payload
from compliance_os.web.services.election_83b import process_election_83b
from compliance_os.web.services.fbar_check import process_fbar_check
from compliance_os.web.services.h1b_doc_check import (
    H1B_FILE_FIELDS,
    process_h1b_doc_check,
    save_uploaded_document,
)
from compliance_os.web.services.mailing_service import (
    build_form_8843_filing_context,
    serialize_filing_context,
)
from compliance_os.web.services.product_catalog import (
    get_product_config,
    list_product_configs,
    serialize_product,
    sync_product_catalog,
)


router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateOrderRequest(BaseModel):
    sku: str


class MarkMailedRequest(BaseModel):
    mailed_at: str | None = None
    tracking_number: str | None = None


def _serialize_artifacts(order: OrderRow, result_data: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for artifact in result_data.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        filename = Path(str(artifact.get("filename") or artifact.get("path") or "")).name
        if not filename:
            continue
        artifacts.append(
            {
                "label": artifact.get("label") or filename,
                "filename": filename,
                "url": f"/api/marketplace/orders/{order.id}/artifacts/{quote(filename)}",
            }
        )
    return artifacts


def _serialize_result_payload(order: OrderRow) -> dict[str, Any]:
    result_data = order.result_data or {}
    findings = list(result_data.get("findings") or [])
    return {
        "order_id": order.id,
        "product_sku": order.product_sku,
        "summary": result_data.get("summary"),
        "findings": findings,
        "finding_count": int(result_data.get("finding_count") or len(findings)),
        "next_steps": list(result_data.get("next_steps") or []),
        "artifacts": _serialize_artifacts(order, result_data),
        "requires_fbar": result_data.get("requires_fbar"),
        "aggregate_max_balance_usd": result_data.get("aggregate_max_balance_usd"),
        "filing_deadline": order.filing_deadline.isoformat() if isinstance(order.filing_deadline, date) else result_data.get("filing_deadline"),
        "document_summary": list(result_data.get("document_summary") or []),
        "comparisons": list(result_data.get("comparisons") or []),
        "mailing_instructions": result_data.get("mailing_instructions"),
    }


def _ensure_marketplace_user(user: UserRow, db: Session) -> MarketplaceUserRow:
    marketplace_user = (
        db.query(MarketplaceUserRow)
        .filter(MarketplaceUserRow.email == user.email)
        .first()
    )
    if marketplace_user is None:
        marketplace_user = MarketplaceUserRow(
            email=user.email,
            source="direct",
            role=user.role or "user",
        )
        db.add(marketplace_user)
        db.flush()
    return marketplace_user


def _require_marketplace_account(
    authorization: str | None,
    db: Session,
) -> tuple[UserRow, MarketplaceUserRow]:
    payload = get_bearer_payload(authorization, db)
    if payload.get("auth_type") != "jwt":
        raise HTTPException(status_code=403, detail="This endpoint requires a web session token")

    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user, _ensure_marketplace_user(user, db)


def _get_owned_order(order_id: str, marketplace_user: MarketplaceUserRow, db: Session) -> OrderRow:
    order = (
        db.query(OrderRow)
        .filter(
            OrderRow.id == order_id,
            OrderRow.user_id == marketplace_user.id,
        )
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _fallback_product(order: OrderRow) -> dict[str, Any]:
    row = order.product
    return serialize_product(
        {
            "sku": order.product_sku,
            "name": row.name if row is not None else order.product_sku,
            "description": row.description if row is not None and row.description else "",
            "price_cents": row.price_cents if row is not None else order.amount_cents,
            "tier": row.tier if row is not None else "tier_0",
            "requires_attorney": row.requires_attorney if row is not None else False,
            "requires_questionnaire": row.requires_questionnaire if row is not None else False,
            "active": row.active if row is not None else True,
            "category": None,
            "filing_method": None,
            "fulfillment_mode": None,
            "headline": None,
            "highlights": [],
            "cta_label": None,
            "path": None,
        }
    )


def _filing_context_from_order(order: OrderRow) -> dict[str, Any]:
    result_data = order.result_data or {}
    context = build_form_8843_filing_context(order.intake_data or {})
    stored_context = result_data.get("filing_context")
    if isinstance(stored_context, dict):
        context.update({key: value for key, value in stored_context.items() if value is not None})

    if order.filing_deadline is not None:
        context["filing_deadline"] = order.filing_deadline
        context["deadline_label"] = order.filing_deadline.strftime("%B %d, %Y")
    context["delivery_method"] = order.delivery_method or context.get("delivery_method")
    context["mailing_status"] = order.mailing_status or context.get("mailing_status")
    context["can_mark_mailed"] = bool(context.get("can_mark_mailed")) and context.get("mailing_status") != "mailed"
    return context


def _serialize_order(order: OrderRow, *, include_result: bool = False) -> dict[str, Any]:
    config = get_product_config(order.product_sku, include_inactive=True)
    product = serialize_product(config) if config is not None else _fallback_product(order)
    result_data = order.result_data or {}

    body: dict[str, Any] = {
        "order_id": order.id,
        "user_id": order.user_id,
        "product_sku": order.product_sku,
        "status": order.status,
        "amount_cents": order.amount_cents,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "delivery_method": order.delivery_method,
        "filing_deadline": order.filing_deadline.isoformat() if isinstance(order.filing_deadline, date) else None,
        "mailing_status": order.mailing_status,
        "mailed_at": order.mailed_at.isoformat() if order.mailed_at else None,
        "tracking_number": order.tracking_number,
        "product": product,
        "intake_complete": bool(order.intake_data),
        "result_ready": bool(result_data),
        "summary": result_data.get("summary"),
        "finding_count": int(result_data.get("finding_count") or len(result_data.get("findings") or [])),
        "next_steps": list(result_data.get("next_steps") or []),
        "artifacts": _serialize_artifacts(order, result_data),
    }

    if order.product_sku == "form_8843_free":
        filing_context = _filing_context_from_order(order)
        body.update(
            {
                "pdf_url": result_data.get("pdf_url"),
                "email_status": result_data.get("email_status"),
                "filing_instructions": serialize_filing_context(filing_context),
                "mailing_service_available": bool(filing_context.get("mailing_service_available")),
            }
        )

    if include_result and result_data:
        body["result"] = _serialize_result_payload(order)

    return body


def _parse_mailed_at(value: str | None) -> datetime:
    if not value:
        return _now()
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ensure_email_sequence(
    db: Session,
    user_id: str,
    sequence_name: str,
    *,
    next_send_at: datetime,
    completed: bool = False,
) -> None:
    existing = (
        db.query(EmailSequenceRow)
        .filter(
            EmailSequenceRow.user_id == user_id,
            EmailSequenceRow.sequence_name == sequence_name,
        )
        .first()
    )
    if existing is None:
        db.add(
            EmailSequenceRow(
                user_id=user_id,
                sequence_name=sequence_name,
                next_send_at=next_send_at,
                current_step=0,
                completed=completed,
            )
        )
        return
    existing.next_send_at = next_send_at
    existing.completed = completed


def _set_deadline_from_iso(order: OrderRow, value: str | None) -> None:
    if not value:
        return
    order.filing_deadline = datetime.strptime(value, "%Y-%m-%d").date()


def _validate_json_intake(order: OrderRow, payload: dict[str, Any]) -> None:
    if order.product_sku == "fbar_check":
        accounts = payload.get("accounts") or []
        if not accounts:
            raise HTTPException(status_code=400, detail="At least one foreign account is required")
        return
    if order.product_sku == "election_83b":
        required_fields = {
            "taxpayer_name",
            "taxpayer_address",
            "company_name",
            "property_description",
            "grant_date",
            "share_count",
            "fair_market_value_per_share",
            "exercise_price_per_share",
            "vesting_schedule",
        }
        missing = [field for field in required_fields if payload.get(field) in (None, "")]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(sorted(missing))}")


@router.get("/products")
def list_products(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> dict[str, list[dict[str, Any]]]:
    sync_product_catalog(db)
    db.commit()
    products = list_product_configs(include_inactive=include_inactive)
    return {"products": [serialize_product(product) for product in products]}


@router.get("/products/{sku}")
def get_product(
    sku: str,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    sync_product_catalog(db)
    db.commit()
    product = get_product_config(sku, include_inactive=include_inactive)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.post("/orders")
def create_order(
    payload: CreateOrderRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    sync_product_catalog(db)

    product = db.get(ProductRow, payload.sku)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.active:
        raise HTTPException(status_code=400, detail="This product is not active yet")

    order = OrderRow(
        user_id=marketplace_user.id,
        product_sku=product.sku,
        status="draft",
        amount_cents=product.price_cents,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _serialize_order(order)


@router.get("/orders")
def list_orders(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, list[dict[str, Any]]]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    orders = (
        db.query(OrderRow)
        .filter(OrderRow.user_id == marketplace_user.id)
        .order_by(OrderRow.created_at.desc())
        .all()
    )
    return {"orders": [_serialize_order(order) for order in orders]}


@router.get("/orders/{order_id}")
def get_order(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    return _serialize_order(_get_owned_order(order_id, marketplace_user, db), include_result=True)


@router.post("/orders/{order_id}/intake")
async def save_order_intake(
    order_id: str,
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)

    if order.product_sku == "h1b_doc_check":
        form = await request.form()
        documents: list[dict[str, Any]] = []
        for field_name, doc_type in H1B_FILE_FIELDS.items():
            candidate = form.get(field_name)
            if not isinstance(candidate, UploadFile) or not candidate.filename:
                continue
            content = await candidate.read()
            saved_path = save_uploaded_document(order.id, candidate.filename, content)
            documents.append(
                {
                    "doc_type": doc_type,
                    "filename": candidate.filename,
                    "path": str(saved_path),
                }
            )
        if not documents:
            raise HTTPException(status_code=400, detail="Upload at least one H-1B packet document")
        intake_data = {"documents": documents}
    else:
        intake_data = await request.json()
        if not isinstance(intake_data, dict):
            raise HTTPException(status_code=400, detail="Intake body must be a JSON object")
        _validate_json_intake(order, intake_data)

    order.intake_data = intake_data
    order.status = "intake_complete"
    order.updated_at = _now()
    db.commit()
    db.refresh(order)
    return _serialize_order(order)


@router.post("/orders/{order_id}/process")
def process_order(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if not order.intake_data:
        raise HTTPException(status_code=400, detail="Complete intake before processing this order")

    order.status = "processing"
    order.updated_at = _now()
    db.flush()

    if order.product_sku == "h1b_doc_check":
        result_data = process_h1b_doc_check(order.id, order.intake_data or {})
        order.delivery_method = "download_only"
        order.mailing_status = "not_required"
    elif order.product_sku == "fbar_check":
        result_data = process_fbar_check(order.id, order.intake_data or {})
        order.delivery_method = "efile"
        order.mailing_status = "not_required"
        _set_deadline_from_iso(order, result_data.get("filing_deadline"))
    elif order.product_sku == "election_83b":
        result_data = process_election_83b(order.id, order.intake_data or {})
        order.delivery_method = "user_mail"
        order.mailing_status = "needs_signature"
        _set_deadline_from_iso(order, result_data.get("filing_deadline"))
        if order.filing_deadline is not None:
            next_send_at = datetime.combine(
                max(order.filing_deadline - timedelta(days=7), date.today()),
                time(hour=9, minute=0),
                tzinfo=timezone.utc,
            )
            _ensure_email_sequence(
                db,
                order.user_id,
                f"election_83b_deadline:{order.id}",
                next_send_at=next_send_at,
                completed=False,
            )
    else:
        raise HTTPException(status_code=400, detail="Processing is not implemented for this product yet")

    order.result_data = result_data
    order.status = "completed"
    order.completed_at = _now()
    order.updated_at = _now()
    db.commit()
    db.refresh(order)
    return _serialize_order(order, include_result=True)


@router.get("/orders/{order_id}/result")
def get_order_result(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if not order.result_data:
        raise HTTPException(status_code=404, detail="Result not ready")
    return _serialize_result_payload(order)


@router.get("/orders/{order_id}/artifacts/{artifact_name}")
def download_artifact(
    order_id: str,
    artifact_name: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> FileResponse:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)

    for artifact in (order.result_data or {}).get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        path = Path(str(artifact.get("path") or ""))
        filename = Path(str(artifact.get("filename") or path.name)).name
        if filename != artifact_name:
            continue
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact file not found")
        return FileResponse(path, filename=filename, media_type="application/pdf")

    raise HTTPException(status_code=404, detail="Artifact not found")


@router.post("/orders/{order_id}/mark-mailed")
def mark_order_mailed(
    order_id: str,
    payload: MarkMailedRequest = Body(default_factory=MarkMailedRequest),
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if order.delivery_method != "user_mail":
        raise HTTPException(status_code=400, detail="This order does not require mailing confirmation")

    order.mailing_status = "mailed"
    order.mailed_at = _parse_mailed_at(payload.mailed_at)
    order.tracking_number = payload.tracking_number or order.tracking_number
    order.updated_at = _now()

    if order.product_sku == "election_83b":
        _ensure_email_sequence(
            db,
            order.user_id,
            f"election_83b_deadline:{order.id}",
            next_send_at=_now(),
            completed=True,
        )

    db.commit()
    db.refresh(order)
    return _serialize_order(order, include_result=True)
