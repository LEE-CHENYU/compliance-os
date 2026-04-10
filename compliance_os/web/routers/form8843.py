"""Public Form 8843 generation endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.database import DATA_DIR, get_session
from compliance_os.web.models.marketplace import (
    EmailSequenceRow,
    MarketplaceUserRow,
    OrderRow,
    ProductRow,
)
from compliance_os.web.services.email_service import send_form_8843_welcome
from compliance_os.web.services.form_8843 import generate_form_8843


router = APIRouter(prefix="/api/form8843", tags=["form8843"])

FORM_8843_OUTPUT_DIR = DATA_DIR / "form_8843"
FORM_8843_PRODUCT = {
    "sku": "form_8843_free",
    "name": "Form 8843 (Free)",
    "description": "Free IRS Form 8843 generator for international students.",
    "price_cents": 0,
    "tier": "tier_0",
    "requires_attorney": False,
    "requires_questionnaire": False,
    "active": True,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Form8843Request(BaseModel):
    email: str
    full_name: str
    visa_type: str
    school_name: str
    country_citizenship: str
    country_passport: str | None = None
    passport_number: str | None = None
    current_nonimmigrant_status: str | None = None
    arrival_date: str | None = None
    school_address: str | None = None
    school_contact: str | None = None
    program_director: str | None = None
    us_taxpayer_id: str | None = None
    address_country: str | None = None
    address_us: str | None = None
    days_present_current: int
    days_present_year_1_ago: int = 0
    days_present_year_2_ago: int = 0
    days_excludable_current: int = 0
    changed_status: bool = False
    applied_for_residency: bool = False


def _get_or_create_user(db: Session, req: Form8843Request) -> MarketplaceUserRow:
    user = db.query(MarketplaceUserRow).filter(MarketplaceUserRow.email == req.email).first()
    if user is not None:
        if not user.full_name and req.full_name:
            user.full_name = req.full_name
        return user

    user = MarketplaceUserRow(
        email=req.email,
        full_name=req.full_name,
        source="form_8843",
        locale="en",
        role="user",
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_product(db: Session) -> ProductRow:
    product = db.get(ProductRow, FORM_8843_PRODUCT["sku"])
    if product is not None:
        return product

    product = ProductRow(**FORM_8843_PRODUCT)
    db.add(product)
    db.flush()
    return product


def _ensure_email_sequence(db: Session, user_id: str) -> None:
    existing = (
        db.query(EmailSequenceRow)
        .filter(
            EmailSequenceRow.user_id == user_id,
            EmailSequenceRow.sequence_name == "form_8843_welcome",
        )
        .first()
    )
    if existing is not None:
        return
    db.add(
        EmailSequenceRow(
            user_id=user_id,
            sequence_name="form_8843_welcome",
            current_step=0,
            next_send_at=_now(),
            completed=False,
        )
    )


@router.post("/generate")
def generate(req: Form8843Request, db: Session = Depends(get_session)) -> dict[str, str]:
    user = _get_or_create_user(db, req)
    product = _get_or_create_product(db)
    pdf_bytes = generate_form_8843(req.model_dump())

    order = OrderRow(
        user_id=user.id,
        product_sku=product.sku,
        status="processing",
        amount_cents=0,
        intake_data=req.model_dump(),
    )
    db.add(order)
    db.flush()

    FORM_8843_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FORM_8843_OUTPUT_DIR / f"{order.id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    email_result = send_form_8843_welcome(req.email, req.full_name, pdf_bytes)
    _ensure_email_sequence(db, user.id)

    order.status = "completed"
    order.completed_at = _now()
    order.result_data = {
        "pdf_path": str(pdf_path),
        "pdf_url": f"/api/form8843/orders/{order.id}/pdf",
        "email_status": email_result.get("status", "unknown"),
    }
    db.commit()

    return {
        "order_id": order.id,
        "user_id": user.id,
        "pdf_url": f"/api/form8843/orders/{order.id}/pdf",
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_session)) -> dict[str, object]:
    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    result_data = order.result_data or {}
    return {
        "order_id": order.id,
        "status": order.status,
        "pdf_url": result_data.get("pdf_url"),
        "email_status": result_data.get("email_status"),
    }


@router.get("/orders/{order_id}/pdf")
def download_pdf(order_id: str, db: Session = Depends(get_session)) -> FileResponse:
    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    result_data = order.result_data or {}
    pdf_path = Path(result_data.get("pdf_path", ""))
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Generated PDF not found")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Form_8843_{order.id}.pdf",
    )
