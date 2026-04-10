"""Public Form 8843 generation endpoints."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
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
from compliance_os.web.services.mailing_service import (
    build_form_8843_filing_context,
    build_form_8843_mailing_kit,
    next_deadline_reminder_at,
    next_mail_reminder_at,
    serialize_filing_context,
)


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
    filing_with_tax_return: bool = False


class MarkMailedRequest(BaseModel):
    mailed_at: str | None = None
    tracking_number: str | None = None


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


def _ensure_email_sequence(
    db: Session,
    user_id: str,
    sequence_name: str,
    *,
    next_send_at: datetime,
    current_step: int = 0,
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
    if existing is not None:
        existing.next_send_at = next_send_at
        existing.current_step = current_step
        existing.completed = completed
        return
    db.add(
        EmailSequenceRow(
            user_id=user_id,
            sequence_name=sequence_name,
            current_step=current_step,
            next_send_at=next_send_at,
            completed=completed,
        )
    )


def _ensure_reminder_sequences(
    db: Session,
    *,
    user_id: str,
    order_id: str,
    filing_context: dict[str, object],
) -> None:
    _ensure_email_sequence(
        db,
        user_id,
        f"form_8843_welcome:{order_id}",
        next_send_at=_now(),
        current_step=1,
        completed=True,
    )

    if not bool(filing_context.get("can_mark_mailed")):
        return

    filing_deadline = filing_context.get("filing_deadline")
    if not isinstance(filing_deadline, date):
        return

    _ensure_email_sequence(
        db,
        user_id,
        f"form_8843_mail_reminder:{order_id}",
        next_send_at=next_mail_reminder_at(),
        completed=False,
    )
    _ensure_email_sequence(
        db,
        user_id,
        f"form_8843_deadline_reminder:{order_id}",
        next_send_at=next_deadline_reminder_at(filing_deadline),
        completed=False,
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
    result_data = order.result_data or {}
    filing_context = _filing_context_from_order(order)
    return {
        "order_id": order.id,
        "status": order.status,
        "pdf_url": result_data.get("pdf_url"),
        "email_status": result_data.get("email_status"),
        "delivery_method": order.delivery_method,
        "filing_deadline": order.filing_deadline.isoformat() if order.filing_deadline else None,
        "mailing_status": order.mailing_status,
        "mailed_at": order.mailed_at.isoformat() if order.mailed_at else None,
        "tracking_number": order.tracking_number,
        "filing_instructions": serialize_filing_context(filing_context),
        "mailing_service_available": bool(filing_context.get("mailing_service_available")),
    }


def _parse_mailed_at(value: str | None) -> datetime:
    if not value:
        return _now()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid mailed_at timestamp") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@router.post("/generate")
def generate(req: Form8843Request, db: Session = Depends(get_session)) -> dict[str, object]:
    user = _get_or_create_user(db, req)
    product = _get_or_create_product(db)
    payload = req.model_dump()
    filing_context = build_form_8843_filing_context(payload)
    pdf_bytes = generate_form_8843(payload)

    order = OrderRow(
        user_id=user.id,
        product_sku=product.sku,
        status="processing",
        amount_cents=0,
        delivery_method=str(filing_context["delivery_method"]),
        filing_deadline=filing_context["filing_deadline"],
        mailing_status=str(filing_context["mailing_status"]),
        intake_data=payload,
    )
    db.add(order)
    db.flush()

    FORM_8843_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FORM_8843_OUTPUT_DIR / f"{order.id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    email_result = send_form_8843_welcome(req.email, req.full_name, pdf_bytes, filing_context)
    _ensure_reminder_sequences(db, user_id=user.id, order_id=order.id, filing_context=filing_context)

    order.status = "completed"
    order.completed_at = _now()
    order.result_data = {
        "pdf_path": str(pdf_path),
        "pdf_url": f"/api/form8843/orders/{order.id}/pdf",
        "email_status": email_result.get("status", "unknown"),
        "filing_context": serialize_filing_context(filing_context),
    }
    db.commit()

    response = _serialize_order(order)
    response["user_id"] = user.id
    return response


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_session)) -> dict[str, object]:
    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize_order(order)


@router.post("/orders/{order_id}/mark-mailed")
def mark_mailed(
    order_id: str,
    payload: MarkMailedRequest = Body(default_factory=MarkMailedRequest),
    db: Session = Depends(get_session),
) -> dict[str, object]:
    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    filing_context = _filing_context_from_order(order)
    if not bool(filing_context.get("can_mark_mailed")) and order.mailing_status != "mailed":
        raise HTTPException(status_code=400, detail="This order does not require standalone mailing confirmation")

    order.mailing_status = "mailed"
    order.mailed_at = _parse_mailed_at(payload.mailed_at)
    order.tracking_number = payload.tracking_number or order.tracking_number
    order.updated_at = _now()
    result_data = dict(order.result_data or {})
    filing_context["mailing_status"] = "mailed"
    filing_context["can_mark_mailed"] = False
    result_data["filing_context"] = serialize_filing_context(filing_context)
    order.result_data = result_data

    sequences = (
        db.query(EmailSequenceRow)
        .filter(
            EmailSequenceRow.user_id == order.user_id,
            EmailSequenceRow.sequence_name.in_(
                [
                    f"form_8843_mail_reminder:{order.id}",
                    f"form_8843_deadline_reminder:{order.id}",
                ]
            ),
        )
        .all()
    )
    for sequence in sequences:
        sequence.completed = True
        sequence.next_send_at = _now()

    db.commit()
    return _serialize_order(order)


@router.get("/orders/{order_id}/mailing-kit")
def get_mailing_kit(order_id: str, db: Session = Depends(get_session)) -> dict[str, object]:
    order = db.get(OrderRow, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    filing_context = _filing_context_from_order(order)
    return {
        "order_id": order.id,
        "mailing_status": order.mailing_status,
        "filing_deadline": order.filing_deadline.isoformat() if order.filing_deadline else None,
        **build_form_8843_mailing_kit(filing_context),
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
