"""Best-effort marketplace intake prefills from the user's extracted documents."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _field_map(doc: DocumentRow) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in doc.extracted_fields:
        if field.field_value not in (None, ""):
            values[field.field_name] = str(field.field_value)
    return values


def _load_user_documents(user_id: str, db: Session) -> list[DocumentRow]:
    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .options(selectinload(DocumentRow.extracted_fields))
        .filter(
            CheckRow.user_id == user_id,
            DocumentRow.is_active.is_(True),
        )
        .all()
    )
    docs.sort(
        key=lambda doc: (
            any(field.field_value not in (None, "") for field in doc.extracted_fields),
            _normalized_uploaded_at(doc),
            doc.id,
        ),
        reverse=True,
    )
    return docs


def _best_document(docs: list[DocumentRow], *doc_types: str) -> DocumentRow | None:
    for doc in docs:
        if doc.doc_type in doc_types:
            return doc
    return None


def _all_documents(docs: list[DocumentRow], *doc_types: str) -> list[DocumentRow]:
    return [doc for doc in docs if doc.doc_type in doc_types]


def _serialize_source_document(doc: DocumentRow) -> dict[str, Any]:
    return {
        "document_id": doc.id,
        "doc_type": doc.doc_type,
        "filename": doc.filename,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


def _prefer(existing: Any, candidate: Any) -> Any:
    if existing not in (None, "", [], {}):
        return existing
    return candidate


def _parse_year(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    raw = str(value)
    for token in raw.replace("/", "-").split("-"):
        if token.isdigit() and len(token) == 4:
            return int(token)
    if raw.isdigit() and len(raw) == 4:
        return int(raw)
    return None


def _parse_amount(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    raw = str(value).replace(",", "").replace("$", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _merge_documents(
    existing: list[dict[str, Any]] | None,
    additions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for document in (existing or []) + additions:
        if not isinstance(document, dict):
            continue
        key = (
            str(document.get("doc_type") or ""),
            str(document.get("source_document_id") or document.get("filename") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(document)
    return merged


def _student_tax_prefill(docs: list[DocumentRow], existing: dict[str, Any]) -> dict[str, Any]:
    applied = dict(existing)
    used_docs: list[DocumentRow] = []

    def apply_from_doc(key: str, doc: DocumentRow | None, field_name: str, *, transform=None, fallback=None) -> None:
        if doc is None:
            return
        fields = _field_map(doc)
        raw = fields.get(field_name)
        if raw in (None, "") and fallback is not None:
            raw = fallback
        if raw in (None, ""):
            return
        candidate = transform(raw) if transform is not None else raw
        applied[key] = _prefer(applied.get(key), candidate)
        if doc not in used_docs:
            used_docs.append(doc)

    passport = _best_document(docs, "passport")
    i20 = _best_document(docs, "i20")
    i94 = _best_document(docs, "i94")
    w2 = _best_document(docs, "w2")
    form_1042s = _best_document(docs, "1042s")
    tax_return = _best_document(docs, "tax_return")

    apply_from_doc("full_name", passport, "full_name")
    apply_from_doc("full_name", i20, "student_name")
    apply_from_doc("full_name", w2, "employee_name")
    apply_from_doc("full_name", form_1042s, "recipient_name")
    apply_from_doc("school_name", i20, "school_name")
    apply_from_doc("country_citizenship", passport, "country_of_issue")
    apply_from_doc("arrival_date", i94, "most_recent_entry_date")
    apply_from_doc("visa_type", i94, "class_of_admission")
    if applied.get("visa_type") in (None, "") and i20 is not None:
        applied["visa_type"] = "F-1"
        if i20 not in used_docs:
            used_docs.append(i20)

    tax_year_candidates = [
        _parse_year(_field_map(doc).get("tax_year"))
        for doc in [w2, form_1042s, tax_return]
        if doc is not None
    ]
    tax_year = max((year for year in tax_year_candidates if year is not None), default=None)
    if tax_year is not None:
        applied["tax_year"] = _prefer(applied.get("tax_year"), tax_year)
        if w2 and w2 not in used_docs:
            used_docs.append(w2)

    wage_income = _parse_amount(_field_map(w2).get("wages_tips_other_compensation") if w2 else None)
    if wage_income is not None:
        applied["wage_income_usd"] = _prefer(applied.get("wage_income_usd"), wage_income)
        if w2 and w2 not in used_docs:
            used_docs.append(w2)

    federal_withholding = _parse_amount(_field_map(w2).get("federal_income_tax_withheld") if w2 else None)
    if federal_withholding is None:
        federal_withholding = _parse_amount(_field_map(form_1042s).get("federal_tax_withheld") if form_1042s else None)
    if federal_withholding is not None:
        applied["federal_withholding_usd"] = _prefer(applied.get("federal_withholding_usd"), federal_withholding)
        if form_1042s and form_1042s not in used_docs:
            used_docs.append(form_1042s)

    other_income = _parse_amount(_field_map(form_1042s).get("gross_income") if form_1042s else None)
    if other_income is not None:
        applied["other_income_usd"] = _prefer(applied.get("other_income_usd"), other_income)
        if form_1042s and form_1042s not in used_docs:
            used_docs.append(form_1042s)

    required_fields = [
        "tax_year",
        "full_name",
        "visa_type",
        "school_name",
        "country_citizenship",
        "arrival_date",
        "days_present_current",
        "days_present_year_1_ago",
        "days_present_year_2_ago",
    ]
    missing_fields = [field for field in required_fields if applied.get(field) in (None, "")]
    applied_field_names = sorted(
        key for key, value in applied.items()
        if value not in (None, "", [], {})
    )
    if applied_field_names:
        summary = f"Pulled {len(applied_field_names)} student-tax intake fields from your data room."
        coverage = "complete" if not missing_fields else "partial"
    else:
        summary = "No student-tax intake fields were found in your data room yet."
        coverage = "empty"

    return {
        "applied_intake": applied,
        "applied_field_names": applied_field_names,
        "missing_fields": missing_fields,
        "coverage": coverage,
        "summary": summary,
        "source_documents": [_serialize_source_document(doc) for doc in used_docs],
    }


def _fbar_prefill(docs: list[DocumentRow], existing: dict[str, Any]) -> dict[str, Any]:
    applied = dict(existing)
    used_docs: list[DocumentRow] = []

    passport = _best_document(docs, "passport")
    if passport is not None:
        fields = _field_map(passport)
        full_name = fields.get("full_name")
        if full_name:
            applied["owner_name"] = _prefer(applied.get("owner_name"), full_name)
            used_docs.append(passport)

    bank_statements = _all_documents(docs, "bank_statement")
    draft_accounts = list(applied.get("accounts") or [])
    if not draft_accounts:
        for doc in bank_statements[:4]:
            fields = _field_map(doc)
            year = _parse_year(fields.get("statement_period_end"))
            if year is not None:
                applied["tax_year"] = _prefer(applied.get("tax_year"), year)
            draft_accounts.append(
                {
                    "institution_name": fields.get("institution_name") or "",
                    "country": "",
                    "account_type": "",
                    "max_balance_usd": _parse_amount(fields.get("ending_balance")) or "",
                    "account_number_last4": "",
                }
            )
            used_docs.append(doc)
    applied["accounts"] = draft_accounts

    missing_fields: list[str] = []
    if not applied.get("owner_name"):
        missing_fields.append("owner_name")
    if not applied.get("tax_year"):
        missing_fields.append("tax_year")
    if not draft_accounts:
        missing_fields.append("accounts")

    coverage = "partial" if used_docs else "empty"
    if used_docs and not missing_fields:
        coverage = "complete"
    summary = (
        f"Pulled {len(used_docs)} bank-document draft account entr{'y' if len(used_docs) == 1 else 'ies'} from your data room."
        if used_docs else
        "No bank statements with extracted fields were found for FBAR prefill."
    )
    return {
        "applied_intake": applied,
        "applied_field_names": ["owner_name", "tax_year", "accounts"] if used_docs else [],
        "missing_fields": missing_fields,
        "coverage": coverage,
        "summary": summary,
        "source_documents": [_serialize_source_document(doc) for doc in used_docs],
    }


def _election_83b_prefill(docs: list[DocumentRow], existing: dict[str, Any]) -> dict[str, Any]:
    applied = dict(existing)
    used_docs: list[DocumentRow] = []

    passport = _best_document(docs, "passport")
    drivers_license = _best_document(docs, "drivers_license")
    ssn_record = _best_document(docs, "social_security_record")
    employment_letter = _best_document(docs, "employment_letter", "employment_contract")
    entity_doc = _best_document(docs, "articles_of_organization", "operating_agreement", "ein_letter")

    for doc, field_name, target in [
        (passport, "full_name", "taxpayer_name"),
        (drivers_license, "address", "taxpayer_address"),
        (ssn_record, "mailing_address", "taxpayer_address"),
        (employment_letter, "employer_name", "company_name"),
        (entity_doc, "entity_name", "company_name"),
    ]:
        if doc is None:
            continue
        value = _field_map(doc).get(field_name)
        if value:
            applied[target] = _prefer(applied.get(target), value)
            if doc not in used_docs:
                used_docs.append(doc)

    applied["property_description"] = _prefer(applied.get("property_description"), "Restricted common stock")
    if used_docs:
        applied_field_names = sorted(
            key for key, value in applied.items()
            if value not in (None, "", [], {})
        )
    else:
        applied_field_names = []

    required_fields = [
        "taxpayer_name",
        "taxpayer_address",
        "company_name",
        "property_description",
        "grant_date",
        "share_count",
        "fair_market_value_per_share",
        "exercise_price_per_share",
        "vesting_schedule",
    ]
    missing_fields = [field for field in required_fields if applied.get(field) in (None, "")]
    coverage = "partial" if used_docs else "empty"
    if used_docs and not missing_fields:
        coverage = "complete"
    summary = (
        f"Pulled {len(applied_field_names)} 83(b) draft fields from your data room."
        if used_docs else
        "No relevant extracted documents were found for 83(b) prefill."
    )
    return {
        "applied_intake": applied,
        "applied_field_names": applied_field_names,
        "missing_fields": missing_fields,
        "coverage": coverage,
        "summary": summary,
        "source_documents": [_serialize_source_document(doc) for doc in used_docs],
    }


def _h1b_prefill(docs: list[DocumentRow], existing: dict[str, Any]) -> dict[str, Any]:
    intake = dict(existing)
    existing_documents = list(intake.get("documents") or [])
    used_docs: list[DocumentRow] = []
    pulled_documents: list[dict[str, Any]] = []
    for doc_type in [
        "h1b_registration",
        "h1b_status_summary",
        "h1b_g28",
        "h1b_filing_invoice",
        "h1b_filing_fee_receipt",
    ]:
        doc = _best_document(docs, doc_type)
        if doc is None:
            continue
        used_docs.append(doc)
        pulled_documents.append(
            {
                "doc_type": doc_type,
                "filename": doc.filename,
                "path": doc.file_path,
                "source_document_id": doc.id,
                "source_doc_type": doc.doc_type,
                "fields": _field_map(doc),
            }
        )

    intake["documents"] = _merge_documents(existing_documents, pulled_documents)
    missing_fields = [
        doc_type for doc_type in [
            "h1b_registration",
            "h1b_status_summary",
            "h1b_g28",
            "h1b_filing_invoice",
            "h1b_filing_fee_receipt",
        ]
        if not any(document.get("doc_type") == doc_type for document in intake.get("documents") or [])
    ]
    coverage = "complete" if intake.get("documents") and not missing_fields else ("partial" if intake.get("documents") else "empty")
    summary = (
        f"Attached {len(used_docs)} H-1B packet documents from your data room."
        if used_docs else
        "No H-1B packet documents were found in your data room yet."
    )
    return {
        "applied_intake": intake,
        "applied_field_names": [document["doc_type"] for document in pulled_documents],
        "missing_fields": missing_fields,
        "coverage": coverage,
        "summary": summary,
        "source_documents": [_serialize_source_document(doc) for doc in used_docs],
    }


def _build_employment_plan_text(doc: DocumentRow | None) -> str | None:
    if doc is None:
        return None
    fields = _field_map(doc)
    employer = fields.get("employer_name")
    title = fields.get("job_title")
    duties = fields.get("duties_description")
    start_date = fields.get("start_date")
    parts = []
    if employer or title:
        parts.append(
            " ".join(part for part in [
                "Employment with",
                employer,
                "as",
                title,
            ] if part)
        )
    if start_date:
        parts.append(f"start date {start_date}")
    if duties:
        parts.append(duties)
    text = ". ".join(part.strip().rstrip(".") for part in parts if part)
    return text.strip() or None


def _opt_prefill(docs: list[DocumentRow], existing: dict[str, Any]) -> dict[str, Any]:
    intake = dict(existing)
    client_intake = dict(intake.get("client_intake") or {})
    existing_documents = list(client_intake.get("documents") or [])
    used_docs: list[DocumentRow] = []
    pulled_documents: list[dict[str, Any]] = []

    mapping: list[tuple[str, tuple[str, ...]]] = [
        ("passport", ("passport",)),
        ("i20_opt_recommendation", ("i20",)),
        ("passport_photo", ("profile_photo",)),
        ("employment_plan", ("employment_letter", "employment_contract")),
    ]
    for intake_doc_type, doc_types in mapping:
        doc = _best_document(docs, *doc_types)
        if doc is None:
            continue
        used_docs.append(doc)
        pulled_documents.append(
            {
                "doc_type": intake_doc_type,
                "filename": doc.filename,
                "path": doc.file_path,
                "source_document_id": doc.id,
                "source_doc_type": doc.doc_type,
            }
        )

    employment_doc = _best_document(docs, "employment_letter", "employment_contract")
    employment_plan_text = _build_employment_plan_text(employment_doc)
    if employment_doc is not None and employment_doc not in used_docs:
        used_docs.append(employment_doc)

    client_intake["documents"] = _merge_documents(existing_documents, pulled_documents)
    if employment_plan_text:
        client_intake["employment_plan_text"] = _prefer(client_intake.get("employment_plan_text"), employment_plan_text)
    client_intake["prefill_preview"] = {
        "forms": ["I-765", "G-28"],
        "supporting_documents": [document["doc_type"] for document in client_intake.get("documents") or []],
        "desired_start_date": client_intake.get("desired_start_date"),
    }
    intake["client_intake"] = client_intake

    missing_fields = []
    if not any(document.get("doc_type") == "passport" for document in client_intake.get("documents") or []):
        missing_fields.append("passport")
    if not any(document.get("doc_type") == "i20_opt_recommendation" for document in client_intake.get("documents") or []):
        missing_fields.append("i20_opt_recommendation")

    coverage = "complete" if client_intake.get("documents") and not missing_fields else ("partial" if client_intake.get("documents") else "empty")
    summary = (
        f"Attached {len(pulled_documents)} OPT intake documents from your data room."
        if pulled_documents else
        "No passport, I-20, or employment-plan documents were found for OPT prefill."
    )
    return {
        "applied_intake": intake,
        "applied_field_names": [document["doc_type"] for document in pulled_documents] + (["employment_plan_text"] if employment_plan_text else []),
        "missing_fields": missing_fields,
        "coverage": coverage,
        "summary": summary,
        "source_documents": [_serialize_source_document(doc) for doc in used_docs],
    }


def build_marketplace_prefill(
    *,
    user_id: str,
    product_sku: str,
    existing_intake: dict[str, Any] | None,
    db: Session,
) -> dict[str, Any]:
    docs = _load_user_documents(user_id, db)
    existing = dict(existing_intake or {})

    if product_sku == "student_tax_1040nr":
        return _student_tax_prefill(docs, existing)
    if product_sku == "fbar_check":
        return _fbar_prefill(docs, existing)
    if product_sku == "election_83b":
        return _election_83b_prefill(docs, existing)
    if product_sku == "h1b_doc_check":
        return _h1b_prefill(docs, existing)
    if product_sku in {"opt_execution", "opt_advisory"}:
        return _opt_prefill(docs, existing)

    return {
        "applied_intake": existing,
        "applied_field_names": [],
        "missing_fields": [],
        "coverage": "empty",
        "summary": "Automatic prefill is not implemented for this product.",
        "source_documents": [],
    }
