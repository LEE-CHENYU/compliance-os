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
from compliance_os.web.models.database import DATA_DIR, get_session
from compliance_os.web.models.marketplace import (
    EmailSequenceRow,
    LimitedScopeAgreementRow,
    MarketplaceUserRow,
    OrderRow,
    ProductRow,
    QuestionnaireResponseRow,
)
from compliance_os.web.services.attorney_workflow import (
    assign_attorney_to_order,
    latest_agreement,
    latest_assignment,
    render_limited_scope_agreement,
    select_available_attorney,
    serialize_assignment,
)
from compliance_os.web.services.auth_service import get_bearer_payload
from compliance_os.web.services.election_83b import process_election_83b
from compliance_os.web.services.email_service import (
    send_attorney_assignment_email,
    send_marketplace_delivery_email,
)
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
from compliance_os.web.services.questionnaire import (
    evaluate,
    normalize_questionnaire_responses,
    serialize_questionnaire_config,
)
from compliance_os.web.services.student_tax_check import process_student_tax_check


router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

OPT_EXECUTION_DIR = DATA_DIR / "marketplace" / "opt_execution"
OPT_EXECUTION_FILE_FIELDS = {
    "passport_file": "passport",
    "i20_file": "i20_opt_recommendation",
    "photo_file": "passport_photo",
    "employment_plan_file": "employment_plan",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CreateOrderRequest(BaseModel):
    sku: str
    questionnaire_response_id: str | None = None
    chosen_mode: str | None = None


class QuestionnaireItemRequest(BaseModel):
    item_id: str
    checked: bool


class QuestionnaireSubmitRequest(BaseModel):
    responses: list[QuestionnaireItemRequest]


class AgreementSignRequest(BaseModel):
    signature: str
    agreement_text_snapshot: str


class MarkMailedRequest(BaseModel):
    mailed_at: str | None = None
    tracking_number: str | None = None


def _record_notification_status(
    result_data: dict[str, Any],
    key: str,
    response: dict[str, str],
) -> None:
    statuses = dict(result_data.get("notification_statuses") or {})
    statuses[key] = response
    result_data["notification_statuses"] = statuses


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


def _save_opt_uploaded_document(order_id: str, filename: str, content: bytes) -> Path:
    order_dir = OPT_EXECUTION_DIR / order_id / "uploads"
    order_dir.mkdir(parents=True, exist_ok=True)
    path = order_dir / filename
    path.write_bytes(content)
    return path


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
        "receipt_number": result_data.get("receipt_number"),
        "filing_confirmation": result_data.get("filing_confirmation"),
        "filed_at": result_data.get("filed_at"),
        "total_income_usd": result_data.get("total_income_usd"),
        "treaty_country": result_data.get("treaty_country"),
        "claim_treaty_benefit": result_data.get("claim_treaty_benefit"),
        "upgrade_offer": result_data.get("upgrade_offer"),
        "notification_statuses": result_data.get("notification_statuses"),
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


def _questionnaire_service_sku(product_sku: str) -> str:
    if product_sku in {"opt_execution", "opt_advisory"}:
        return "opt_execution"
    return product_sku


def _serialize_agreement(order: OrderRow) -> dict[str, Any] | None:
    agreement = latest_agreement(order)
    if agreement is None:
        return None
    return {
        "agreement_id": agreement.id,
        "signed_at": agreement.signed_at.isoformat() if agreement.signed_at else None,
        "user_signature": agreement.user_signature,
    }


def _serialize_order(order: OrderRow, *, include_result: bool = False) -> dict[str, Any]:
    config = get_product_config(order.product_sku, include_inactive=True)
    product = serialize_product(config) if config is not None else _fallback_product(order)
    result_data = order.result_data or {}
    intake_data = order.intake_data or {}
    assignment = latest_assignment(order)

    intake_complete = bool(order.intake_data)
    if order.product_sku in {"opt_execution", "opt_advisory"}:
        intake_complete = bool(intake_data.get("client_intake"))

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
        "intake_complete": intake_complete,
        "result_ready": bool(result_data),
        "summary": result_data.get("summary"),
        "finding_count": int(result_data.get("finding_count") or len(result_data.get("findings") or [])),
        "next_steps": list(result_data.get("next_steps") or []),
        "artifacts": _serialize_artifacts(order, result_data),
        "questionnaire_response_id": intake_data.get("questionnaire_response_id"),
        "chosen_mode": intake_data.get("chosen_mode"),
        "agreement_signed": latest_agreement(order) is not None,
        "agreement": _serialize_agreement(order),
        "attorney_assignment": serialize_assignment(assignment),
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
    if order.product_sku == "student_tax_1040nr":
        required_fields = {
            "tax_year",
            "full_name",
            "visa_type",
            "school_name",
            "country_citizenship",
            "arrival_date",
            "days_present_current",
            "days_present_year_1_ago",
            "days_present_year_2_ago",
        }
        missing = [field for field in required_fields if payload.get(field) in (None, "")]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(sorted(missing))}")
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


@router.get("/products/{sku}/questionnaire")
def get_product_questionnaire(
    sku: str,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    sync_product_catalog(db)
    db.commit()
    product = get_product_config(sku, include_inactive=True)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not bool(product.get("requires_questionnaire")):
        raise HTTPException(status_code=400, detail="This product does not use a questionnaire")
    return serialize_questionnaire_config(_questionnaire_service_sku(sku))


@router.post("/products/{sku}/questionnaire")
def submit_product_questionnaire(
    sku: str,
    payload: QuestionnaireSubmitRequest,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    sync_product_catalog(db)
    product = db.get(ProductRow, sku)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.requires_questionnaire:
        raise HTTPException(status_code=400, detail="This product does not use a questionnaire")

    normalized_responses = normalize_questionnaire_responses([item.model_dump() for item in payload.responses])
    evaluation = evaluate(sku, normalized_responses)
    response_row = QuestionnaireResponseRow(
        user_id=marketplace_user.id,
        service_sku=product.sku,
        responses=normalized_responses,
        recommendation=evaluation.recommendation,
    )
    db.add(response_row)
    db.commit()
    db.refresh(response_row)
    return {
        "questionnaire_response_id": response_row.id,
        "recommendation": evaluation.recommendation,
        "advisory_reason": evaluation.advisory_reason,
        "execution_reason": evaluation.execution_reason,
        "missing_required_items": evaluation.missing_required_items,
        "complexity_flags": evaluation.complexity_flags,
    }


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

    intake_data: dict[str, Any] | None = None
    status = "draft"
    delivery_method = "download_only"
    mailing_status = "not_required"

    if product.requires_questionnaire:
        if not payload.questionnaire_response_id:
            raise HTTPException(status_code=400, detail="Questionnaire response is required for this product")
        questionnaire_response = (
            db.query(QuestionnaireResponseRow)
            .filter(
                QuestionnaireResponseRow.id == payload.questionnaire_response_id,
                QuestionnaireResponseRow.user_id == marketplace_user.id,
            )
            .first()
        )
        if questionnaire_response is None:
            raise HTTPException(status_code=404, detail="Questionnaire response not found")
        chosen_mode = payload.chosen_mode or questionnaire_response.recommendation or "execution"
        if product.sku == "opt_execution" and chosen_mode != "execution":
            raise HTTPException(status_code=400, detail="OPT Execution orders must use chosen_mode=execution")
        if product.sku == "opt_advisory" and chosen_mode != "advisory":
            raise HTTPException(status_code=400, detail="OPT Advisory orders must use chosen_mode=advisory")
        intake_data = {
            "questionnaire_response_id": questionnaire_response.id,
            "chosen_mode": chosen_mode,
            "questionnaire_recommendation": questionnaire_response.recommendation,
            "questionnaire_responses": questionnaire_response.responses,
        }
        status = "agreement_pending"
        delivery_method = "attorney_filing"

    order = OrderRow(
        user_id=marketplace_user.id,
        product_sku=product.sku,
        status=status,
        amount_cents=product.price_cents,
        delivery_method=delivery_method,
        mailing_status=mailing_status,
        intake_data=intake_data,
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


@router.get("/orders/{order_id}/agreement")
def get_order_agreement(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if order.product_sku not in {"opt_execution", "opt_advisory"}:
        raise HTTPException(status_code=400, detail="This order does not use a limited-scope agreement")

    attorney = latest_assignment(order).attorney if latest_assignment(order) is not None else None
    agreement = latest_agreement(order)
    agreement_text = agreement.agreement_text if agreement is not None else render_limited_scope_agreement(order, marketplace_user, attorney)
    return {
        "order_id": order.id,
        "agreement_text": agreement_text,
        "signed": agreement is not None,
        "agreement": _serialize_agreement(order),
    }


@router.post("/orders/{order_id}/sign-agreement")
def sign_order_agreement(
    order_id: str,
    payload: AgreementSignRequest,
    request: Request,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if order.product_sku not in {"opt_execution", "opt_advisory"}:
        raise HTTPException(status_code=400, detail="This order does not use a limited-scope agreement")
    if not payload.signature.strip():
        raise HTTPException(status_code=400, detail="Typed signature is required")
    if not (order.intake_data or {}).get("client_intake"):
        raise HTTPException(status_code=400, detail="Complete OPT intake before signing the agreement")

    if latest_agreement(order) is not None:
        raise HTTPException(status_code=400, detail="Agreement already signed")

    attorney = latest_assignment(order).attorney if latest_assignment(order) is not None else None
    if attorney is None:
        attorney = select_available_attorney(db)
    if attorney is None:
        raise HTTPException(status_code=400, detail="No attorney is currently available")

    agreement = LimitedScopeAgreementRow(
        order_id=order.id,
        user_id=marketplace_user.id,
        attorney_id=attorney.id,
        agreement_text=payload.agreement_text_snapshot,
        user_signature=payload.signature.strip(),
        user_ip=request.client.host if request.client is not None else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(agreement)
    assignment = assign_attorney_to_order(order, db)
    order.status = "attorney_review"
    order.updated_at = _now()
    result_data = dict(order.result_data or {})
    _record_notification_status(
        result_data,
        "attorney_assignment_email",
        send_attorney_assignment_email(
            attorney.email,
            attorney_name=attorney.full_name,
            client_name=marketplace_user.full_name or marketplace_user.email,
            product_name=order.product.name if order.product is not None else order.product_sku,
        ),
    )
    order.result_data = result_data
    db.commit()
    db.refresh(order)
    db.refresh(agreement)
    db.refresh(assignment)
    return {
        "agreement_id": agreement.id,
        "signed_at": agreement.signed_at.isoformat() if agreement.signed_at else None,
        "order": _serialize_order(order, include_result=True),
        "attorney_assignment": serialize_assignment(assignment),
    }


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
    elif order.product_sku in {"opt_execution", "opt_advisory"}:
        form = await request.form()
        documents: list[dict[str, Any]] = []
        for field_name, doc_type in OPT_EXECUTION_FILE_FIELDS.items():
            candidate = form.get(field_name)
            if not isinstance(candidate, UploadFile) or not candidate.filename:
                continue
            content = await candidate.read()
            saved_path = _save_opt_uploaded_document(order.id, candidate.filename, content)
            documents.append(
                {
                    "doc_type": doc_type,
                    "filename": candidate.filename,
                    "path": str(saved_path),
                }
            )
        desired_start_date = str(form.get("desired_start_date") or "").strip()
        employment_plan_text = str(form.get("employment_plan_text") or "").strip()
        if not documents and not desired_start_date and not employment_plan_text:
            raise HTTPException(status_code=400, detail="Provide OPT intake details before saving")
        existing = dict(order.intake_data or {})
        existing["client_intake"] = {
            "desired_start_date": desired_start_date or None,
            "employment_plan_text": employment_plan_text or None,
            "documents": documents,
            "prefill_preview": {
                "forms": ["I-765", "G-28"],
                "supporting_documents": [document["doc_type"] for document in documents],
                "desired_start_date": desired_start_date or None,
            },
        }
        intake_data = existing
    else:
        intake_data = await request.json()
        if not isinstance(intake_data, dict):
            raise HTTPException(status_code=400, detail="Intake body must be a JSON object")
        _validate_json_intake(order, intake_data)

    order.intake_data = intake_data
    if order.product_sku in {"opt_execution", "opt_advisory"}:
        order.status = "intake_complete" if latest_agreement(order) is None else "attorney_review"
    else:
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
    elif order.product_sku == "student_tax_1040nr":
        result_data = process_student_tax_check(order.id, order.intake_data or {})
        order.delivery_method = "tax_return_package"
        order.mailing_status = "not_required"
        _set_deadline_from_iso(order, result_data.get("filing_deadline"))
        if order.filing_deadline is not None:
            next_send_at = datetime.combine(
                max(order.filing_deadline - timedelta(days=14), date.today()),
                time(hour=9, minute=0),
                tzinfo=timezone.utc,
            )
            _ensure_email_sequence(
                db,
                order.user_id,
                f"student_tax_1040nr_deadline:{order.id}",
                next_send_at=next_send_at,
                completed=False,
            )
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

    _record_notification_status(
        result_data,
        "delivery_email",
        send_marketplace_delivery_email(
            marketplace_user.email,
            full_name=marketplace_user.full_name or marketplace_user.email,
            product_name=order.product.name if order.product is not None else order.product_sku,
            summary=str(result_data.get("summary") or "Your result is ready."),
            next_steps=[str(step) for step in result_data.get("next_steps") or []],
            filing_deadline=order.filing_deadline.isoformat() if order.filing_deadline is not None else None,
        ),
    )
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


@router.post("/orders/{order_id}/accept-upgrade")
def accept_order_upgrade(
    order_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    _, marketplace_user = _require_marketplace_account(authorization, db)
    order = _get_owned_order(order_id, marketplace_user, db)
    if order.product_sku != "opt_execution":
        raise HTTPException(status_code=400, detail="Only OPT Execution orders can be upgraded here")

    result_data = dict(order.result_data or {})
    upgrade_offer = dict(result_data.get("upgrade_offer") or {})
    if order.status != "flagged" or not upgrade_offer:
        raise HTTPException(status_code=400, detail="No upgrade offer is available for this order")

    accepted_order_id = str(upgrade_offer.get("accepted_order_id") or "").strip()
    if accepted_order_id:
        upgraded_order = db.get(OrderRow, accepted_order_id)
        if upgraded_order is None:
            raise HTTPException(status_code=404, detail="Previously accepted advisory order was not found")
        return {
            "accepted": True,
            "original_order": _serialize_order(order, include_result=True),
            "upgraded_order": _serialize_order(upgraded_order, include_result=True),
        }

    advisory_product = db.get(ProductRow, "opt_advisory")
    if advisory_product is None or not advisory_product.active:
        raise HTTPException(status_code=400, detail="OPT Advisory is not available")

    intake_data = dict(order.intake_data or {})
    intake_data["chosen_mode"] = "advisory"

    upgraded_order = OrderRow(
        user_id=marketplace_user.id,
        product_sku=advisory_product.sku,
        status="agreement_pending",
        amount_cents=advisory_product.price_cents,
        delivery_method="attorney_filing",
        mailing_status="not_required",
        intake_data=intake_data,
    )
    db.add(upgraded_order)
    db.flush()

    upgrade_offer["accepted_order_id"] = upgraded_order.id
    upgrade_offer["accepted_at"] = _now().isoformat()
    result_data["upgrade_offer"] = upgrade_offer
    order.result_data = result_data
    order.updated_at = _now()

    db.commit()
    db.refresh(order)
    db.refresh(upgraded_order)
    return {
        "accepted": True,
        "original_order": _serialize_order(order, include_result=True),
        "upgraded_order": _serialize_order(upgraded_order, include_result=True),
    }
