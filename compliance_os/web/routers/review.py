"""Compare, evaluate, followups, snapshot endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas_v2 import (
    Comparison,
    Finding,
    Followup,
    FollowupAnswer,
    Snapshot,
)
from compliance_os.web.models.tables_v2 import (
    CheckRow,
    ComparisonRow,
    DocumentRow,
    ExtractedFieldRow,
    FindingRow,
    FollowupRow,
)
from compliance_os.web.services.comparator import compare_fields
from compliance_os.web.services.document_store import document_series_key_for_document
from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

router = APIRouter(prefix="/api/checks/{check_id}", tags=["review"])

# Track A field mapping: comparison_field → (i983_field, employment_letter_field, match_type)
STEM_OPT_FIELD_MAP = {
    "job_title": ("job_title", "job_title", "fuzzy"),
    "employer_name": ("employer_name", "employer_name", "exact"),
    "work_location": ("work_site_address", "work_location", "fuzzy"),
    "start_date": ("start_date", "start_date", "exact"),
    "compensation": ("compensation", "compensation", "numeric"),
    "duties": ("duties_description", "duties_description", "semantic"),
    "supervisor": ("supervisor_name", "manager_name", "fuzzy"),
    "full_time": ("full_time", "full_time", "exact"),
}

# Student track field mapping: I-20 CPT fields vs employment letter
# I-20 extraction uses same fields as i983 (employer_name, start_date, etc.)
STUDENT_FIELD_MAP = {
    "employer_name": ("employer_name", "employer_name", "exact"),
    "work_location": ("work_site_address", "work_location", "fuzzy"),
    "start_date": ("start_date", "start_date", "exact"),
    "full_time": ("full_time", "full_time", "exact"),
}

# Track B field mapping: comparison_field → (answer_key, extraction_field, match_type)
# Compares user answers against tax return extraction
ENTITY_FIELD_MAP = {
    "entity_type": ("entity_type", "form_type", "logic"),
    "form_5472": ("entity_type", "form_5472_present", "logic"),
    "form_type": ("owner_residency", "form_type", "logic"),
}

# Data-room observation mapping: comparison_field → (doc_type, extraction_field, detail)
DATA_ROOM_OBSERVED_FIELDS = {
    "paystub_employer_name": ("paystub", "employer_name", "Extracted from latest paystub"),
    "paystub_pay_period_end": ("paystub", "pay_period_end", "Extracted from latest paystub"),
    "paystub_net_pay": ("paystub", "net_pay", "Extracted from latest paystub"),
    "employment_letter_employee_name": ("employment_letter", "employee_name", "Extracted from latest employment letter"),
    "employment_letter_employer_name": ("employment_letter", "employer_name", "Extracted from latest employment letter"),
    "employment_letter_job_title": ("employment_letter", "job_title", "Extracted from latest employment letter"),
    "employment_letter_start_date": ("employment_letter", "start_date", "Extracted from latest employment letter"),
    "i9_employee_name": ("i9", "employee_name", "Extracted from latest Form I-9"),
    "i9_employee_first_day_of_employment": ("i9", "employee_first_day_of_employment", "Extracted from latest Form I-9"),
    "i9_citizenship_status": ("i9", "citizenship_status", "Extracted from latest Form I-9"),
    "everify_case_number": ("e_verify_case", "case_number", "Extracted from latest E-Verify case record"),
    "everify_case_status": ("e_verify_case", "case_status", "Extracted from latest E-Verify case record"),
    "everify_employee_first_day_of_employment": ("e_verify_case", "employee_first_day_of_employment", "Extracted from latest E-Verify case record"),
    "i765_applicant_name": ("i765", "applicant_name", "Extracted from latest Form I-765"),
    "i765_eligibility_category": ("i765", "eligibility_category", "Extracted from latest Form I-765"),
    "i765_application_reason": ("i765", "application_reason", "Extracted from latest Form I-765"),
    "h1b_registration_number": ("h1b_registration", "registration_number", "Extracted from latest H-1B registration record"),
    "h1b_employer_name": ("h1b_registration", "employer_name", "Extracted from latest H-1B registration record"),
    "h1b_employer_ein": ("h1b_registration", "employer_ein", "Extracted from latest H-1B registration record"),
    "h1b_status_title": ("h1b_status_summary", "status_title", "Extracted from latest H-1B status summary"),
    "h1b_registration_window_end_date": (
        "h1b_status_summary",
        "registration_window_end_date",
        "Extracted from latest H-1B status summary",
    ),
    "h1b_petition_filing_window_end_date": (
        "h1b_status_summary",
        "petition_filing_window_end_date",
        "Extracted from latest H-1B status summary",
    ),
    "h1b_g28_representative_name": ("h1b_g28", "representative_name", "Extracted from latest DHS Form G-28"),
    "h1b_g28_client_entity_name": ("h1b_g28", "client_entity_name", "Extracted from latest DHS Form G-28"),
    "h1b_invoice_number": ("h1b_filing_invoice", "invoice_number", "Extracted from latest H-1B filing invoice"),
    "h1b_invoice_total_due_amount": (
        "h1b_filing_invoice",
        "total_due_amount",
        "Extracted from latest H-1B filing invoice",
    ),
    "h1b_invoice_beneficiary_name": (
        "h1b_filing_invoice",
        "beneficiary_name",
        "Extracted from latest H-1B filing invoice",
    ),
    "h1b_receipt_transaction_id": (
        "h1b_filing_fee_receipt",
        "transaction_id",
        "Extracted from latest H-1B filing fee receipt",
    ),
    "h1b_receipt_response_message": (
        "h1b_filing_fee_receipt",
        "response_message",
        "Extracted from latest H-1B filing fee receipt",
    ),
    "h1b_receipt_amount": ("h1b_filing_fee_receipt", "amount", "Extracted from latest H-1B filing fee receipt"),
    "h1b_receipt_cardholder_name": (
        "h1b_filing_fee_receipt",
        "cardholder_name",
        "Extracted from latest H-1B filing fee receipt",
    ),
    "cpt_application_student_name": ("cpt_application", "student_name", "Extracted from latest CPT application"),
    "cpt_application_employer_name": ("cpt_application", "employer_name", "Extracted from latest CPT application"),
    "cpt_application_approval_date": ("cpt_application", "approval_date", "Extracted from latest CPT application"),
    "i20_student_name": ("i20", "student_name", "Extracted from latest Form I-20"),
    "i20_program_end_date": ("i20", "program_end_date", "Extracted from latest Form I-20"),
    "i20_travel_signature_date": ("i20", "travel_signature_date", "Extracted from latest Form I-20"),
    "i94_class_of_admission": ("i94", "class_of_admission", "Extracted from latest Form I-94 record"),
    "i94_most_recent_entry_date": ("i94", "most_recent_entry_date", "Extracted from latest Form I-94 record"),
    "i94_admit_until_date": ("i94", "admit_until_date", "Extracted from latest Form I-94 record"),
    "passport_full_name": ("passport", "full_name", "Extracted from latest passport identity page"),
    "passport_date_of_birth": ("passport", "date_of_birth", "Extracted from latest passport identity page"),
    "passport_expiration_date": (
        "passport",
        "expiration_date",
        "Extracted from latest passport identity page",
    ),
    "ead_full_name": ("ead", "full_name", "Extracted from latest EAD card"),
    "ead_date_of_birth": ("ead", "date_of_birth", "Extracted from latest EAD card"),
    "ead_card_expires_on": ("ead", "card_expires_on", "Extracted from latest EAD card"),
    "resume_candidate_name": ("resume", "candidate_name", "Extracted from latest resume"),
    "resume_primary_title": ("resume", "primary_title", "Extracted from latest resume"),
    "resume_email": ("resume", "email", "Extracted from latest resume"),
    "w2_employee_name": ("w2", "employee_name", "Extracted from latest Form W-2"),
    "w2_tax_year": ("w2", "tax_year", "Extracted from latest Form W-2"),
    "tax_return_form_type": ("tax_return", "form_type", "Extracted from latest tax return"),
    "tax_return_tax_year": ("tax_return", "tax_year", "Extracted from latest tax return"),
    "form_1042s_recipient_name": ("1042s", "recipient_name", "Extracted from latest Form 1042-S"),
    "form_1042s_tax_year": ("1042s", "tax_year", "Extracted from latest Form 1042-S"),
}


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


def _get_extracted_dict(check: CheckRow, doc_type: str) -> dict[str, str | None]:
    """Get extracted fields from the most relevant document for a doc type."""
    doc = _select_document(check, doc_type)
    if doc:
        return {f.field_name: f.field_value for f in doc.extracted_fields}
    return {}


def _select_document(check: CheckRow, doc_type: str) -> DocumentRow | None:
    """Prefer the newest document with extracted values for a document type."""
    candidates = [doc for doc in check.documents if doc.doc_type == doc_type]
    if not candidates:
        return None

    def _sort_key(doc: DocumentRow):
        has_values = any(field.field_value not in (None, "") for field in doc.extracted_fields)
        return has_values, _normalized_uploaded_at(doc), doc.id

    return max(candidates, key=_sort_key)


def _add_extracted_observation(
    *,
    check_id: str,
    field_name: str,
    value: str | None,
    detail: str,
    db: Session,
    results: list[ComparisonRow],
) -> None:
    value_str = (value or "").strip()
    if not value_str:
        return

    row = ComparisonRow(
        check_id=check_id,
        field_name=field_name,
        value_a=None,
        value_b=value_str,
        match_type="extracted",
        status="match",
        confidence=1.0,
        detail=detail,
    )
    db.add(row)
    results.append(row)


def _entity_type_comparison(
    entity_type: str,
    owner_residency: str,
    form_type: str,
) -> tuple[str, float, str | None]:
    """Compare claimed entity type to the filing form with basic tax-election awareness."""
    if not entity_type or not form_type:
        return "needs_review", 0.0, "Missing entity type or filing form"

    if entity_type == "not_sure":
        return "needs_review", 0.0, "Entity type was not provided with certainty"

    if entity_type == "s_corp":
        return (
            ("match", 1.0, None)
            if form_type == "1120-S"
            else ("mismatch", 0.0, "S-corporations should generally file Form 1120-S")
        )

    if entity_type == "c_corp":
        return (
            ("match", 1.0, None)
            if form_type == "1120"
            else ("mismatch", 0.0, "C-corporations should generally file Form 1120")
        )

    if entity_type == "multi_llc":
        if form_type == "1065":
            return "match", 1.0, None
        return "needs_review", 0.5, "Multi-member LLCs may elect corporate treatment; verify the intended tax election"

    if entity_type == "smllc":
        if owner_residency != "us_citizen_or_pr" and form_type in {"1040", "1040-NR"}:
            return (
                "needs_review",
                0.5,
                "A personal return alone does not validate foreign-owned single-member LLC compliance; confirm Form 5472 + pro forma 1120 treatment",
            )
        if form_type == "1120-S":
            return "mismatch", 0.0, "Single-member LLCs cannot file Form 1120-S without an S-corp election"
        if form_type in {"1040", "1040-NR", "1120"}:
            return "match", 1.0, None
        return "needs_review", 0.5, "Confirm how the LLC elected to be taxed"

    return "needs_review", 0.0, "Unsupported entity type"


@router.post("/compare", response_model=list[Comparison])
def run_comparison(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Clear old comparisons
    for old in check.comparisons:
        db.delete(old)

    results = []

    if check.track == "entity":
        # Track B: compare answers vs tax return extraction
        tax = _get_extracted_dict(check, "tax_return")
        answers = check.answers or {}

        # Human-readable entity type labels
        ENTITY_LABELS = {"smllc": "Single-member LLC", "multi_llc": "Multi-member LLC", "c_corp": "C-Corporation", "s_corp": "S-Corporation", "not_sure": "Not sure"}

        # Entity type vs filing type
        entity_type = answers.get("entity_type", "")
        owner_residency = answers.get("owner_residency", "")
        form_type = tax.get("form_type", "")
        entity_status, entity_confidence, entity_detail = _entity_type_comparison(
            entity_type,
            owner_residency,
            str(form_type),
        )
        row = ComparisonRow(
            check_id=check_id,
            field_name="entity_type",
            value_a=ENTITY_LABELS.get(entity_type, entity_type),
            value_b=form_type,
            match_type="logic",
            status=entity_status,
            confidence=entity_confidence,
            detail=entity_detail,
        )
        db.add(row)
        results.append(row)

        # Form 5472 check
        is_foreign = answers.get("owner_residency") != "us_citizen_or_pr"
        is_smllc = answers.get("entity_type") == "smllc"
        f5472 = tax.get("form_5472_present", "")
        if is_foreign and is_smllc:
            filed = str(f5472).lower() == "true"
            status = "match" if filed else "mismatch"
            row = ComparisonRow(check_id=check_id, field_name="form_5472", value_a="Required (foreign-owned LLC)", value_b="Filed" if filed else "Not found in return", match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
            db.add(row)
            results.append(row)

        # Filing form type check (1040 vs 1040-NR)
        if is_foreign and form_type:
            status = "mismatch" if form_type == "1040" else "match"
            row = ComparisonRow(check_id=check_id, field_name="form_type", value_a="Non-US person — should file 1040-NR", value_b=f"Filed {form_type}", match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
            db.add(row)
            results.append(row)

        # EIN match (just extract and show)
        ein = tax.get("ein")
        if ein:
            row = ComparisonRow(check_id=check_id, field_name="ein", value_a=None, value_b=ein, match_type="exact", status="match", confidence=1.0, detail="Extracted from return")
            db.add(row)
            results.append(row)

        # Entity name
        entity_name = tax.get("entity_name")
        if entity_name:
            row = ComparisonRow(check_id=check_id, field_name="entity_name", value_a=None, value_b=entity_name, match_type="exact", status="match", confidence=1.0, detail="Extracted from return")
            db.add(row)
            results.append(row)

    elif check.track == "student":
        # Student track: compare I-20 vs employment letter (only if both exist)
        i20 = _get_extracted_dict(check, "i20")
        emp = _get_extracted_dict(check, "employment_letter")

        # Only run CPT cross-checks if employment letter was uploaded
        if emp:
            for comp_field, (a_field, b_field, match_type) in STUDENT_FIELD_MAP.items():
                if match_type == "semantic":
                    row = ComparisonRow(check_id=check_id, field_name=comp_field, value_a=i20.get(a_field), value_b=emp.get(b_field), match_type="semantic", status="needs_review", confidence=0.5, detail="Semantic comparison")
                else:
                    cr = compare_fields(comp_field, i20.get(a_field), emp.get(b_field), match_type)
                    row = ComparisonRow(check_id=check_id, field_name=cr.field_name, value_a=cr.value_a, value_b=cr.value_b, match_type=cr.match_type, status=cr.status, confidence=cr.confidence, detail=cr.detail)
                db.add(row)
                results.append(row)

    elif check.track == "data_room":
        extracted_by_doc_type = {
            "paystub": _get_extracted_dict(check, "paystub"),
            "employment_letter": _get_extracted_dict(check, "employment_letter"),
            "i9": _get_extracted_dict(check, "i9"),
            "e_verify_case": _get_extracted_dict(check, "e_verify_case"),
            "i765": _get_extracted_dict(check, "i765"),
            "h1b_registration": _get_extracted_dict(check, "h1b_registration"),
            "h1b_status_summary": _get_extracted_dict(check, "h1b_status_summary"),
            "h1b_g28": _get_extracted_dict(check, "h1b_g28"),
            "h1b_filing_invoice": _get_extracted_dict(check, "h1b_filing_invoice"),
            "h1b_filing_fee_receipt": _get_extracted_dict(check, "h1b_filing_fee_receipt"),
            "cpt_application": _get_extracted_dict(check, "cpt_application"),
            "i20": _get_extracted_dict(check, "i20"),
            "i94": _get_extracted_dict(check, "i94"),
            "passport": _get_extracted_dict(check, "passport"),
            "ead": _get_extracted_dict(check, "ead"),
            "resume": _get_extracted_dict(check, "resume"),
            "w2": _get_extracted_dict(check, "w2"),
            "tax_return": _get_extracted_dict(check, "tax_return"),
            "1042s": _get_extracted_dict(check, "1042s"),
        }

        for comp_field, (doc_type, extraction_field, detail) in DATA_ROOM_OBSERVED_FIELDS.items():
            _add_extracted_observation(
                check_id=check_id,
                field_name=comp_field,
                value=extracted_by_doc_type[doc_type].get(extraction_field),
                detail=detail,
                db=db,
                results=results,
            )

        employment_letter = extracted_by_doc_type["employment_letter"]
        i9 = extracted_by_doc_type["i9"]
        everify = extracted_by_doc_type["e_verify_case"]
        h1b_registration = extracted_by_doc_type["h1b_registration"]
        h1b_g28 = extracted_by_doc_type["h1b_g28"]
        h1b_invoice = extracted_by_doc_type["h1b_filing_invoice"]
        h1b_receipt = extracted_by_doc_type["h1b_filing_fee_receipt"]
        cpt_application = extracted_by_doc_type["cpt_application"]
        i20 = extracted_by_doc_type["i20"]
        i94 = extracted_by_doc_type["i94"]
        passport = extracted_by_doc_type["passport"]
        ead = extracted_by_doc_type["ead"]
        resume = extracted_by_doc_type["resume"]
        w2 = extracted_by_doc_type["w2"]
        tax_return = extracted_by_doc_type["tax_return"]
        form_1042s = extracted_by_doc_type["1042s"]

        cross_document_checks = [
            (
                "employment_letter_i9_employee_name",
                employment_letter.get("employee_name"),
                i9.get("employee_name"),
                "fuzzy",
                "Cross-document identity check between employment letter and Form I-9",
            ),
            (
                "employment_letter_paystub_employer_name",
                employment_letter.get("employer_name"),
                extracted_by_doc_type["paystub"].get("employer_name"),
                "fuzzy",
                "Cross-document employer consistency check between employment letter and paystub",
            ),
            (
                "i9_everify_employee_name",
                i9.get("employee_name"),
                everify.get("employee_name"),
                "fuzzy",
                "Cross-document consistency check between Form I-9 and E-Verify",
            ),
            (
                "i9_everify_first_day_of_employment",
                i9.get("employee_first_day_of_employment"),
                everify.get("employee_first_day_of_employment"),
                "exact",
                "Cross-document consistency check between Form I-9 and E-Verify",
            ),
            (
                "h1b_registration_g28_entity_name",
                h1b_registration.get("employer_name"),
                h1b_g28.get("client_entity_name"),
                "fuzzy",
                "Cross-document consistency check between H-1B registration and G-28 client entity",
            ),
            (
                "h1b_registration_invoice_petitioner_name",
                h1b_registration.get("employer_name"),
                h1b_invoice.get("petitioner_name"),
                "fuzzy",
                "Cross-document consistency check between H-1B registration and filing invoice petitioner",
            ),
            (
                "h1b_registration_receipt_signatory_name",
                h1b_registration.get("authorized_individual_name"),
                h1b_receipt.get("cardholder_name"),
                "fuzzy",
                "Cross-document consistency check between H-1B registration signatory and payment receipt cardholder",
            ),
            (
                "h1b_invoice_receipt_beneficiary_name",
                h1b_invoice.get("beneficiary_name"),
                h1b_receipt.get("cardholder_name"),
                "fuzzy",
                "Cross-document consistency check between filing invoice beneficiary and payment receipt cardholder",
            ),
            (
                "cpt_application_i20_student_name",
                cpt_application.get("student_name"),
                i20.get("student_name"),
                "fuzzy",
                "Cross-document student identity check between CPT application and Form I-20",
            ),
            (
                "cpt_application_employment_letter_employer_name",
                cpt_application.get("employer_name"),
                employment_letter.get("employer_name"),
                "fuzzy",
                "Cross-document employer consistency check between CPT application and employment letter",
            ),
            (
                "i20_passport_student_name",
                i20.get("student_name"),
                passport.get("full_name"),
                "fuzzy",
                "Cross-document identity check between Form I-20 and passport",
            ),
            (
                "i20_ead_student_name",
                i20.get("student_name"),
                ead.get("full_name"),
                "fuzzy",
                "Cross-document identity check between Form I-20 and EAD",
            ),
            (
                "resume_passport_candidate_name",
                resume.get("candidate_name"),
                passport.get("full_name"),
                "fuzzy",
                "Cross-document identity check between resume and passport",
            ),
            (
                "passport_ead_date_of_birth",
                passport.get("date_of_birth"),
                ead.get("date_of_birth"),
                "exact",
                "Cross-document identity check between passport and EAD date of birth",
            ),
            (
                "passport_w2_employee_name",
                passport.get("full_name"),
                w2.get("employee_name"),
                "fuzzy",
                "Cross-document identity check between passport and Form W-2 employee name",
            ),
            (
                "passport_1042s_recipient_name",
                passport.get("full_name"),
                form_1042s.get("recipient_name"),
                "fuzzy",
                "Cross-document identity check between passport and Form 1042-S recipient",
            ),
            (
                "w2_tax_return_tax_year",
                w2.get("tax_year"),
                tax_return.get("tax_year"),
                "exact",
                "Cross-document tax-year consistency check between Form W-2 and tax return",
            ),
            (
                "1042s_tax_return_tax_year",
                form_1042s.get("tax_year"),
                tax_return.get("tax_year"),
                "exact",
                "Cross-document tax-year consistency check between Form 1042-S and tax return",
            ),
            (
                "i94_i20_class_of_admission",
                i94.get("class_of_admission"),
                "F-1" if i20 else None,
                "exact",
                "Travel-status consistency check: I-94 class of admission should be F-1 when an I-20 is present",
            ),
        ]

        for comp_field, value_a, value_b, match_type, default_detail in cross_document_checks:
            if value_a is None and value_b is None:
                continue
            cr = compare_fields(comp_field, value_a, value_b, match_type)
            row = ComparisonRow(
                check_id=check_id,
                field_name=cr.field_name,
                value_a=cr.value_a,
                value_b=cr.value_b,
                match_type=cr.match_type,
                status=cr.status,
                confidence=cr.confidence,
                detail=cr.detail or default_detail,
            )
            db.add(row)
            results.append(row)

    else:
        # Track A: compare I-983 vs employment letter
        i983 = _get_extracted_dict(check, "i983")
        emp = _get_extracted_dict(check, "employment_letter")

        for comp_field, (a_field, b_field, match_type) in STEM_OPT_FIELD_MAP.items():
            if match_type == "semantic":
                row = ComparisonRow(
                    check_id=check_id, field_name=comp_field,
                    value_a=i983.get(a_field), value_b=emp.get(b_field),
                    match_type="semantic", status="needs_review", confidence=0.5,
                    detail="Semantic comparison requires LLM evaluation",
                )
            else:
                cr = compare_fields(comp_field, i983.get(a_field), emp.get(b_field), match_type)
                row = ComparisonRow(
                    check_id=check_id, field_name=cr.field_name,
                    value_a=cr.value_a, value_b=cr.value_b,
                    match_type=cr.match_type, status=cr.status,
                    confidence=cr.confidence, detail=cr.detail,
                )
            db.add(row)
            results.append(row)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/comparisons", response_model=list[Comparison])
def get_comparisons(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.comparisons


@router.post("/evaluate", response_model=list[Finding])
def run_evaluation(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Build evaluation context
    i983 = _get_extracted_dict(check, "i983")
    i20 = _get_extracted_dict(check, "i20")
    emp = _get_extracted_dict(check, "employment_letter")
    tax = _get_extracted_dict(check, "tax_return")

    comp_dict = {}
    for c in check.comparisons:
        comp_dict[c.field_name] = {"status": c.status, "confidence": c.confidence}

    if check.track == "entity":
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a={},
            extraction_b=tax or {},
            comparisons=comp_dict,
        )
    elif check.track == "student":
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a=i20 or {},
            extraction_b=emp or {},
            comparisons=comp_dict,
        )
    elif check.track == "data_room":
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a={},
            extraction_b={},
            comparisons=comp_dict,
        )
    else:
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a=i983 or {},
            extraction_b=emp or {},
            comparisons=comp_dict,
        )

    # Load rules based on track
    rule_file = str(PROJECT_ROOT / "config" / "rules" / f"{check.track}.yaml")
    engine = RuleEngine.from_yaml(rule_file)

    # Clear old findings
    for old in check.findings:
        db.delete(old)

    findings_out = []
    for fr in engine.evaluate(ctx):
        row = FindingRow(
            check_id=check_id,
            rule_id=fr.rule_id,
            rule_version=engine.version,
            severity=fr.severity,
            category=fr.category,
            title=fr.title,
            action=fr.action,
            consequence=fr.consequence,
            immigration_impact=fr.immigration_impact,
        )
        db.add(row)
        findings_out.append(row)

    check.status = "reviewed"
    db.commit()
    for r in findings_out:
        db.refresh(r)
    return findings_out


@router.get("/findings", response_model=list[Finding])
def get_findings(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.findings


@router.get("/followups", response_model=list[Followup])
def get_followups(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.followups


@router.post("/followups", response_model=list[Followup])
def generate_followups(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Clear old followups
    for old in check.followups:
        db.delete(old)

    # Generate human-readable follow-up questions.
    # Never spit jargon — translate field mismatches into plain English.
    PLAIN_QUESTIONS: dict[str, dict] = {
        # Track A (stem_opt) field mismatches
        "job_title": {
            "question": "Your documents show two different job titles. What is your actual current job title?",
            "chips_fn": lambda a, b: [a, b, "Something else"] if a and b else ["Enter your title"],
        },
        "work_location": {
            "question": "Where do you actually work day-to-day? Your documents show different locations.",
            "chips_fn": lambda a, b: [a or "Office location", b or "Other location", "I work remotely"],
        },
        "compensation": {
            "question": "Your documents show different salary amounts. What is your actual annual compensation?",
            "chips_fn": lambda a, b: [a, b, "Different amount"] if a and b else ["Enter amount"],
        },
        "start_date": {
            "question": "Your documents show different employment start dates. When did you actually start working?",
            "chips_fn": lambda a, b: [a, b, "Different date"] if a and b else ["Enter date"],
        },
        "employer_name": {
            "question": "The employer name doesn't match across your documents. What is the exact legal name of your employer?",
            "chips_fn": lambda a, b: [a, b, "Something else"] if a and b else ["Enter employer name"],
        },
        "supervisor": {
            "question": "Your documents list different supervisors. Who is your current direct supervisor?",
            "chips_fn": lambda a, b: [a, b, "Someone else"] if a and b else ["Enter name"],
        },
        "full_time": {
            "question": "Is your position full-time or part-time?",
            "chips_fn": lambda a, b: ["Full-time", "Part-time"],
        },
        "duties": {
            "question": "Do your daily work responsibilities closely relate to your degree field?",
            "chips_fn": lambda a, b: ["Yes, closely related", "Somewhat related", "Not directly related"],
        },
        # Track B (entity) field mismatches
        "entity_type": {
            "question": "We found a mismatch between your entity type and how your tax return was filed. Did you or your CPA choose to file as an S-Corporation?",
            "chips_fn": lambda a, b: ["Yes, intentionally", "No, that seems wrong", "Not sure"],
        },
        "form_5472": {
            "question": "As a foreign-owned LLC, you're required to file Form 5472 every year — even with zero revenue. Have you ever filed this form?",
            "chips_fn": lambda a, b: ["Yes, I've filed it", "No, never heard of it", "Not sure"],
        },
        "form_type": {
            "question": "Your tax return was filed as a standard 1040. As a non-US person, you may need to file 1040-NR instead. Did your CPA discuss this with you?",
            "chips_fn": lambda a, b: ["Yes, we discussed it", "No, I used TurboTax", "Not sure"],
        },
    }

    # Fallback for any field not in the lookup
    def _default_question(field: str, val_a: str | None, val_b: str | None) -> tuple[str, list[str]]:
        name = field.replace("_", " ")
        return (
            f"We found a discrepancy in your {name}. Can you confirm which is correct?",
            [val_a or "Option A", val_b or "Option B", "Not sure"],
        )

    followups = []
    for comp in check.comparisons:
        if comp.status in ("mismatch", "needs_review"):
            # Skip questions where both values are missing — nothing useful to ask
            if not comp.value_a and not comp.value_b:
                continue
            # Skip needs_review where one side is entirely empty (document didn't extract)
            if comp.status == "needs_review" and (not comp.value_a or not comp.value_b):
                continue

            entry = PLAIN_QUESTIONS.get(comp.field_name)
            if entry:
                q_text = entry["question"]
                chips = entry["chips_fn"](comp.value_a, comp.value_b)
            else:
                q_text, chips = _default_question(comp.field_name, comp.value_a, comp.value_b)

            row = FollowupRow(
                check_id=check_id,
                question_key=f"{comp.field_name}_mismatch",
                question_text=q_text,
                chips=chips,
            )
            db.add(row)
            followups.append(row)

    db.commit()
    for r in followups:
        db.refresh(r)
    return followups


@router.patch("/followups/{followup_id}", response_model=Followup)
def answer_followup(
    check_id: str,
    followup_id: str,
    body: FollowupAnswer,
    db: Session = Depends(get_session),
):
    row = db.get(FollowupRow, followup_id)
    if not row or row.check_id != check_id:
        raise HTTPException(404, "Followup not found")
    row.answer = body.answer
    row.answered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.get("/snapshot", response_model=Snapshot)
def get_snapshot(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    extractions = {}
    for doc_type in {doc.doc_type for doc in check.documents}:
        doc = _select_document(check, doc_type)
        if doc:
            extractions[doc_type] = doc.extracted_fields

    document_extractions = []
    for doc in sorted(check.documents, key=lambda d: (_normalized_uploaded_at(d), d.id)):
        document_extractions.append(
            {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "document_family": doc.document_family,
                "document_series_key": doc.document_series_key or document_series_key_for_document(doc),
                "document_version": doc.document_version or 1,
                "is_active": doc.is_active is not False,
                "filename": doc.filename,
                "source_path": doc.source_path,
                "uploaded_at": doc.uploaded_at,
                "ocr_engine": doc.ocr_engine,
                "provenance": doc.provenance or {},
                "extracted_fields": doc.extracted_fields,
            }
        )

    findings = [f for f in check.findings if f.category != "advisory"]
    advisories = [f for f in check.findings if f.category == "advisory"]

    return {
        "check": check,
        "extractions": extractions,
        "document_extractions": document_extractions,
        "comparisons": check.comparisons,
        "findings": findings,
        "followups": check.followups,
        "advisories": advisories,
    }
