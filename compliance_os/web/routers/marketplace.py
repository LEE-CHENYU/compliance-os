"""Marketplace catalog endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.marketplace import MarketplaceUserRow, OrderRow
from compliance_os.web.services.auth_service import get_bearer_payload
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


def _require_marketplace_account(
    authorization: str | None,
    db: Session,
) -> tuple[UserRow, MarketplaceUserRow | None]:
    payload = get_bearer_payload(authorization, db)
    if payload.get("auth_type") != "jwt":
        raise HTTPException(status_code=403, detail="This endpoint requires a web session token")

    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    marketplace_user = (
        db.query(MarketplaceUserRow)
        .filter(MarketplaceUserRow.email == user.email)
        .first()
    )
    return user, marketplace_user


def _fallback_product(order: OrderRow) -> dict[str, object]:
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


def _filing_context_from_order(order: OrderRow) -> dict[str, object]:
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


def _serialize_order(order: OrderRow) -> dict[str, object]:
    config = get_product_config(order.product_sku, include_inactive=True)
    product = serialize_product(config) if config is not None else _fallback_product(order)
    body: dict[str, object] = {
        "order_id": order.id,
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
        "result_ready": bool(order.result_data),
    }

    if order.product_sku == "form_8843_free":
        result_data = order.result_data or {}
        filing_context = _filing_context_from_order(order)
        body.update(
            {
                "pdf_url": result_data.get("pdf_url"),
                "email_status": result_data.get("email_status"),
                "filing_instructions": serialize_filing_context(filing_context),
                "mailing_service_available": bool(filing_context.get("mailing_service_available")),
            }
        )

    return body


@router.get("/products")
def list_products(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> dict[str, list[dict[str, object]]]:
    sync_product_catalog(db)
    db.commit()
    products = list_product_configs(include_inactive=include_inactive)
    return {"products": [serialize_product(product) for product in products]}


@router.get("/products/{sku}")
def get_product(
    sku: str,
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> dict[str, object]:
    sync_product_catalog(db)
    db.commit()
    product = get_product_config(sku, include_inactive=include_inactive)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.get("/orders")
def list_orders(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, list[dict[str, object]]]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    if marketplace_user is None:
        return {"orders": []}

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
) -> dict[str, object]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    if marketplace_user is None:
        raise HTTPException(status_code=404, detail="Order not found")

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
    return _serialize_order(order)
