"""Dashboard helpers for surfacing marketplace service state."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.marketplace import MarketplaceUserRow, OrderRow
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow
from compliance_os.web.services.product_catalog import get_product_config, serialize_product
from compliance_os.web.services.timeline_builder import canonical_documents_for_checks


_FORM_8843_EXEMPT_STAGES = {"pre_completion", "opt", "stem_opt"}
_FORM_8843_STATUS_DOC_TYPES = {
    "i20",
    "i20_opt_recommendation",
    "enrollment_verification",
    "student_id",
    "transcript",
    "admission_letter",
}
_INCOME_DOC_TYPES = {"w2", "1042s", "1099"}
_H1B_DOC_TYPES = {
    "h1b_registration",
    "h1b_registration_worksheet",
    "h1b_registration_checklist",
    "h1b_status_summary",
    "h1b_g28",
    "h1b_filing_invoice",
    "h1b_filing_fee_receipt",
    "g_28",
    "g28",
}
_OPT_DOC_TYPES = {"i20_opt_recommendation", "i765", "ead"}
_ACTIVE_ORDER_STATUSES = {
    "draft",
    "intake_complete",
    "agreement_pending",
    "attorney_review",
    "ready_to_file",
    "flagged",
    "processing",
}
_REUSABLE_ORDER_STATUSES = {
    "draft",
    "intake_complete",
    "agreement_pending",
    "attorney_review",
    "ready_to_file",
    "flagged",
    "processing",
}


def _product_payload(sku: str) -> dict[str, Any]:
    config = get_product_config(sku, include_inactive=True)
    if config is None:
        return {
            "sku": sku,
            "name": sku,
            "public_name": None,
            "description": "",
            "public_description": None,
            "price_cents": 0,
            "tier": "tier_0",
            "requires_attorney": False,
            "requires_questionnaire": False,
            "active": True,
            "category": None,
            "filing_method": None,
            "fulfillment_mode": None,
            "headline": None,
            "public_headline": None,
            "highlights": [],
            "public_highlights": [],
            "cta_label": None,
            "public_cta_label": None,
            "path": f"/services/{sku}",
        }
    return serialize_product(config)


def _dashboard_category(category: str | None) -> str:
    if category == "startup":
        return "business"
    return category or "other"


def _days_until(deadline: date | None) -> int | None:
    if deadline is None:
        return None
    return (deadline - date.today()).days


def _years_in_us_value(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _is_form_8843_candidate(checks: list[CheckRow], docs: list[DocumentRow]) -> bool:
    for check in checks:
        answers = check.answers or {}
        stage = str(answers.get("stage") or "").strip().lower()
        years_in_us = _years_in_us_value(answers.get("years_in_us"))

        if check.track == "student":
            return True
        if check.track == "stem_opt" and stage in _FORM_8843_EXEMPT_STAGES and (years_in_us is None or years_in_us < 6):
            return True
        if (
            check.track == "entity"
            and str(answers.get("owner_residency") or "").strip().lower() == "on_visa"
            and str(answers.get("visa_type") or "").strip().lower() == "f1_opt_stem"
        ):
            return True

    for doc in docs:
        if doc.doc_type in _FORM_8843_STATUS_DOC_TYPES:
            return True
        if doc.doc_type == "i94":
            for field in doc.extracted_fields:
                if field.field_name == "class_of_admission" and str(field.field_value or "").strip().upper() in {"F-1", "J-1", "M-1", "Q-1"}:
                    return True
    return False


def _has_income_signal(docs: list[DocumentRow]) -> bool:
    return any(doc.doc_type in _INCOME_DOC_TYPES for doc in docs)


def _timeline_text_blob(timeline_payload: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for bucket in ("advisories", "findings", "integrity_issues"):
        for item in timeline_payload.get(bucket) or []:
            if not isinstance(item, Mapping):
                continue
            for key in ("title", "action", "consequence", "message", "text"):
                value = item.get(key)
                if value:
                    parts.append(str(value))
    return " \n".join(parts).lower()


def _has_fbar_signal(docs: list[DocumentRow], text_blob: str) -> bool:
    if any(doc.doc_type == "bank_statement" for doc in docs):
        return True
    return any(token in text_blob for token in ("fbar", "fincen 114", "foreign bank", "foreign account", "8938"))


def _has_h1b_signal(docs: list[DocumentRow], text_blob: str) -> bool:
    if any(doc.doc_type in _H1B_DOC_TYPES for doc in docs):
        return True
    return any(token in text_blob for token in ("h-1b", "h1b", "i-129", "petition packet"))


def _has_opt_signal(docs: list[DocumentRow], checks: list[CheckRow], text_blob: str) -> bool:
    if any(doc.doc_type in _OPT_DOC_TYPES for doc in docs):
        return True
    for check in checks:
        stage = str((check.answers or {}).get("stage") or "").strip().lower()
        if stage in {"pre_completion", "opt"}:
            return True
    return "opt" in text_blob


def _has_83b_signal(text_blob: str) -> bool:
    return any(token in text_blob for token in ("83(b)", "83b", "restricted stock", "founder stock", "equity grant"))


def _order_status_label(status: str) -> str:
    return status.replace("_", " ").strip().title()


def _order_next_action(order: OrderRow) -> str:
    if order.product_sku == "form_8843_free":
        if order.mailing_status == "mailed":
            return "Form 8843 marked as mailed."
        return "Print, sign, and mail your Form 8843."
    if order.product_sku == "student_tax_1040nr":
        return "Review the tax package and file before the deadline."
    if order.product_sku == "fbar_check":
        return "Review the FinCEN guidance and file if the threshold was met."
    if order.product_sku == "election_83b":
        if order.mailing_status == "mailed":
            return "83(b) election marked as mailed."
        return "Print, sign, and send the 83(b) election by certified mail."
    if order.status == "draft":
        return "Complete the intake to start this service."
    if order.status == "intake_complete":
        return "Run the review to generate the result."
    if order.status == "processing":
        return "Guardian is processing this service."
    if order.status == "agreement_pending":
        return "Finish intake and sign the attorney agreement."
    if order.status == "attorney_review":
        return "Attorney review is in progress."
    if order.status == "ready_to_file":
        return "Attorney review is complete and the filing can proceed."
    if order.status == "flagged":
        return "Review the flagged complexity and upgrade recommendation."
    if order.status == "completed":
        return "Review the result and next steps."
    return "Open the service workspace."


def _is_active_order(order: OrderRow) -> bool:
    if order.status in _ACTIVE_ORDER_STATUSES:
        return True
    if order.mailing_status not in {"not_required", "mailed"}:
        return True
    if order.product_sku in {"student_tax_1040nr", "fbar_check"} and order.filing_deadline is not None:
        return True
    return False


def _collapse_duplicate_reusable_orders(orders: list[OrderRow]) -> list[OrderRow]:
    collapsed: list[OrderRow] = []
    seen_reusable_skus: set[str] = set()
    for order in orders:
        is_reusable = (
            order.status in _REUSABLE_ORDER_STATUSES
            and order.completed_at is None
            and not (order.result_data or {})
        )
        if is_reusable:
            if order.product_sku in seen_reusable_skus:
                continue
            seen_reusable_skus.add(order.product_sku)
        collapsed.append(order)
    return collapsed


def _attention_state(order: OrderRow) -> str:
    days = _days_until(order.filing_deadline)
    if order.status == "flagged" or order.mailing_status == "needs_signature" or (days is not None and days <= 14):
        return "urgent"
    if _is_active_order(order):
        return "active"
    return "complete"


def _serialize_order_card(order: OrderRow) -> dict[str, Any]:
    product = _product_payload(order.product_sku)
    summary = str(
        (order.result_data or {}).get("summary")
        or product.get("public_headline")
        or product.get("headline")
        or product.get("public_description")
        or product.get("description")
        or ""
    ).strip()
    days = _days_until(order.filing_deadline)
    return {
        "order_id": order.id,
        "product_sku": order.product_sku,
        "product_name": product.get("public_name") or product["name"],
        "product": product,
        "status": order.status,
        "status_label": _order_status_label(order.status),
        "attention_state": _attention_state(order),
        "summary": summary,
        "next_action": _order_next_action(order),
        "filing_deadline": order.filing_deadline.isoformat() if order.filing_deadline else None,
        "deadline_days": days,
        "mailing_status": order.mailing_status,
        "href": f"/account/orders/{order.id}",
        "cta_label": "Resume",
    }


def _deadline_title(order: OrderRow) -> str:
    if order.product_sku == "form_8843_free":
        return "Form 8843 mailing deadline"
    if order.product_sku == "student_tax_1040nr":
        return "Student tax package deadline"
    if order.product_sku == "fbar_check":
        return "FBAR filing deadline"
    if order.product_sku == "election_83b":
        return "83(b) election deadline"
    product = _product_payload(order.product_sku)
    return f"{product.get('public_name') or product['name']} deadline"


def _serialize_service_deadline(order: OrderRow) -> dict[str, Any] | None:
    if order.filing_deadline is None:
        return None
    days = _days_until(order.filing_deadline)
    if days is None:
        return None
    return {
        "title": _deadline_title(order),
        "date": order.filing_deadline.isoformat(),
        "days": days,
        "category": _dashboard_category(_product_payload(order.product_sku).get("category")),
        "severity": "critical" if days < 0 else "warning" if days < 30 else "info",
        "action": _order_next_action(order),
        "order_id": order.id,
        "product_sku": order.product_sku,
    }


def _serialize_recommendation(sku: str, *, reason: str, priority: int) -> dict[str, Any]:
    product = _product_payload(sku)
    return {
        "sku": sku,
        "name": product.get("public_name") or product["name"],
        "reason": reason,
        "priority": priority,
        "product": product,
        "href": product.get("path") or f"/services/{sku}",
        "cta_label": product.get("public_cta_label") or product.get("cta_label") or ("Generate for free" if product.get("price_cents") == 0 else "Start service"),
    }


def _recommended_services(
    *,
    checks: list[CheckRow],
    docs: list[DocumentRow],
    orders: list[OrderRow],
    timeline_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    existing_skus = {order.product_sku for order in orders}
    text_blob = _timeline_text_blob(timeline_payload)
    form_8843_candidate = _is_form_8843_candidate(checks, docs)
    recommendations: list[dict[str, Any]] = []

    if form_8843_candidate and "form_8843_free" not in existing_skus and "student_tax_1040nr" not in existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "form_8843_free",
                reason="Your dashboard looks like an F-1, OPT, STEM OPT, or similar exempt-visitor case. Form 8843 is often required annually even when you are already working or running a company.",
                priority=100,
            )
        )

    if form_8843_candidate and _has_income_signal(docs) and "student_tax_1040nr" not in existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "student_tax_1040nr",
                reason="Your data room shows nonresident-status signals plus income documents, so the 1040-NR package is the more complete tax workflow.",
                priority=110,
            )
        )

    if _has_fbar_signal(docs, text_blob) and "fbar_check" not in existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "fbar_check",
                reason="Your dashboard has foreign-account signals, so an FBAR threshold review is a natural next step.",
                priority=90,
            )
        )

    if _has_h1b_signal(docs, text_blob) and "h1b_doc_check" not in existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "h1b_doc_check",
                reason="Your documents suggest an H-1B packet or petition context, so the document review belongs in the main workflow.",
                priority=85,
            )
        )

    if _has_opt_signal(docs, checks, text_blob) and not {"opt_execution", "opt_advisory"} & existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "opt_execution",
                reason="Your dashboard still looks student- or OPT-oriented, so the OPT workflow should be accessible directly from here.",
                priority=80,
            )
        )

    if _has_83b_signal(text_blob) and "election_83b" not in existing_skus:
        recommendations.append(
            _serialize_recommendation(
                "election_83b",
                reason="Your dashboard includes founder-stock or 83(b) language, so the time-sensitive election packet should be one click away.",
                priority=75,
            )
        )

    recommendations.sort(key=lambda item: (-int(item["priority"]), item["name"]))
    return recommendations[:4]


def build_dashboard_service_summary(
    *,
    user: UserRow,
    timeline_payload: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    checks = db.query(CheckRow).filter(CheckRow.user_id == user.id).all()
    docs = canonical_documents_for_checks(checks)
    marketplace_user = (
        db.query(MarketplaceUserRow)
        .filter(MarketplaceUserRow.email == user.email)
        .first()
    )
    orders: list[OrderRow] = []
    if marketplace_user is not None:
        orders = (
            db.query(OrderRow)
            .filter(OrderRow.user_id == marketplace_user.id)
            .order_by(OrderRow.updated_at.desc(), OrderRow.created_at.desc())
            .all()
        )
        orders = _collapse_duplicate_reusable_orders(orders)

    active_orders = [_serialize_order_card(order) for order in orders if _is_active_order(order)]
    recent_completed = [
        _serialize_order_card(order)
        for order in orders
        if order.completed_at is not None and not _is_active_order(order)
    ][:3]
    recommended_services = _recommended_services(
        checks=checks,
        docs=docs,
        orders=orders,
        timeline_payload=timeline_payload,
    )
    service_deadlines = [
        deadline
        for order in orders
        for deadline in [_serialize_service_deadline(order)]
        if deadline is not None
    ]
    service_deadlines.sort(key=lambda item: (int(item["days"]), str(item["title"])))

    return {
        "active_orders": active_orders,
        "recent_completed": recent_completed,
        "recommended_services": recommended_services,
        "service_deadlines": service_deadlines,
        "stats": {
            "active_orders": len(active_orders),
            "recent_completed": len(recent_completed),
            "recommended_services": len(recommended_services),
        },
    }
