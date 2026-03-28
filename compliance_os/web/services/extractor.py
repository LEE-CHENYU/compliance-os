"""LLM extraction service — PDF text → structured LLM output → extracted fields."""
from __future__ import annotations

import importlib
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from typing import Any

import os

import fitz  # PyMuPDF

from compliance_os.web.services.llm_runtime import extract_json

logger = logging.getLogger(__name__)


@dataclass
class TextExtractionResult:
    text: str
    engine: str
    metadata: dict[str, Any]


SCHEMAS: dict[str, dict[str, str]] = {
    "articles_of_organization": {
        "entity_name": "Legal name of the company or LLC",
        "filing_state": "State where the articles were filed",
        "filing_date": "Date the articles were filed (YYYY-MM-DD)",
        "entity_id": "State filing number or entity identification number",
        "registered_agent_name": "Name of the registered agent",
        "registered_agent_address": "Physical address of the registered agent",
        "mailing_address": "Mailing address of the company if shown",
        "principal_office_address": "Principal office address of the company if shown",
    },
    "certificate_of_good_standing": {
        "entity_name": "Legal name of the entity",
        "jurisdiction": "Jurisdiction or state issuing the certificate",
        "entity_type": "Entity type such as Limited Liability Company",
        "formation_date": "Date the entity was formed or qualified (YYYY-MM-DD)",
        "entity_id": "State entity identification number",
        "standing_status": "Current standing status stated in the certificate",
        "duration": "Entity duration if stated, such as Perpetual",
    },
    "registered_agent_consent": {
        "entity_name": "Name of the business entity",
        "registered_agent_name": "Name of the registered agent",
        "registered_office_address": "Registered office physical address",
        "consent_date": "Date the consent was signed (YYYY-MM-DD)",
        "signer_name": "Printed name of the signer if present",
        "signer_title": "Title of the signer if present",
    },
    "i983": {
        "student_name": "Full name of the student",
        "sevis_number": "SEVIS number (format: N followed by 10 digits)",
        "school_name": "Name of the school or university",
        "degree_level": "Degree level (Bachelor's, Master's, Doctoral)",
        "major": "Major field of study",
        "employer_name": "Name of the employer",
        "employer_ein": "Employer EIN (format: XX-XXXXXXX)",
        "employer_address": "Employer mailing address",
        "work_site_address": "Physical work site address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD)",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly, stipend)",
        "duties_description": "Description of job duties and responsibilities",
        "training_goals": "Training goals and objectives",
        "supervisor_name": "Supervisor / mentor name",
        "supervisor_title": "Supervisor title",
        "supervisor_phone": "Supervisor phone number",
        "full_time": "Full-time employment (true/false)",
    },
    "employment_letter": {
        "employee_name": "Employee full name",
        "employer_name": "Employer / company name",
        "employer_address": "Employer address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD) or null if ongoing",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly)",
        "duties_description": "Description of job duties and responsibilities",
        "manager_name": "Manager / supervisor name",
        "full_time": "Full-time or part-time (true for full-time)",
        "work_location": "Work location / office address",
    },
    "tax_return": {
        "form_type": "Tax form type (1040, 1040-NR, 1120, 1120-S, 1065)",
        "tax_year": "Tax year (number)",
        "entity_name": "Entity name (for business returns) or null",
        "ein": "EIN (format: XX-XXXXXXX) or null",
        "filing_status": "Filing status (Single, MFJ, etc.) or null",
        "total_income": "Total income amount (number)",
        "schedules_present": "List of schedules present (e.g., schedule_c, schedule_d, schedule_nec)",
        "form_5472_present": "Whether Form 5472 is attached (true/false)",
        "form_3520_present": "Whether Form 3520 is attached (true/false)",
        "form_8938_present": "Whether Form 8938 is attached (true/false)",
        "state_returns_filed": "List of state abbreviations for state returns filed",
    },
    "i20": {
        "student_name": "Full name of the student",
        "sevis_number": "SEVIS number (format: N followed by 10 digits)",
        "school_name": "Name of the school or university",
        "program": "Program name and degree level (e.g., Master's in Computer Science)",
        "major": "Major field of study",
        "program_start_date": "Program start date (YYYY-MM-DD)",
        "program_end_date": "Program end date (YYYY-MM-DD)",
        "employer_name": "CPT employer name if CPT is authorized, otherwise null",
        "work_site_address": "CPT work location/address if authorized, otherwise null",
        "start_date": "CPT employment start date (YYYY-MM-DD) if authorized, otherwise null",
        "end_date": "CPT employment end date (YYYY-MM-DD) if authorized, otherwise null",
        "full_time": "CPT full-time or part-time (true for full-time, false for part-time, null if no CPT)",
        "travel_signature_date": "Most recent DSO travel signature date (YYYY-MM-DD) if visible",
    },
    "i94": {
        "admission_number": "Admission number from the I-94 record",
        "most_recent_entry_date": "Most recent date of entry into the United States (YYYY-MM-DD)",
        "class_of_admission": "Class of admission, such as F-1 or H-1B",
        "admit_until_date": "Admit until date (YYYY-MM-DD), or D/S if that is what is shown",
        "port_of_entry": "Port of entry if visible",
    },
    "ead": {
        "card_number": "Card number on the Employment Authorization Document",
        "uscis_number": "USCIS number / A-number if visible",
        "category": "Category code shown on the card, such as C03C",
        "card_expires_on": "Card expiration date (YYYY-MM-DD)",
        "date_of_birth": "Date of birth (YYYY-MM-DD) if visible",
        "full_name": "Full name on the card",
    },
    "w2": {
        "tax_year": "Tax year for the W-2 (number)",
        "employee_name": "Employee full name",
        "employer_name": "Employer name",
        "employer_ein": "Employer EIN (format: XX-XXXXXXX)",
        "wages_tips_other_compensation": "Box 1 wages, tips, other compensation (number only)",
        "federal_income_tax_withheld": "Federal income tax withheld (number only)",
        "social_security_wages": "Social security wages (number only)",
        "state": "State abbreviation in boxes 15-20 if visible",
    },
    "ein_letter": {
        "entity_name": "Legal business name associated with the EIN",
        "ein": "Employer identification number (format: XX-XXXXXXX)",
        "assigned_date": "Date the EIN was assigned (YYYY-MM-DD) if visible",
        "business_address": "Business mailing address if visible",
    },
    "passport": {
        "full_name": "Passport holder full name",
        "passport_number": "Passport number",
        "country_of_issue": "Issuing country or authority",
        "date_of_birth": "Date of birth (YYYY-MM-DD)",
        "issue_date": "Passport issue date (YYYY-MM-DD) if visible",
        "expiration_date": "Passport expiration date (YYYY-MM-DD)",
    },
    "1042s": {
        "tax_year": "Tax year associated with the Form 1042-S (number)",
        "recipient_name": "Name of the recipient/payee",
        "recipient_address": "Recipient mailing address",
        "recipient_account_number": "Recipient account number if shown",
        "date_of_birth": "Recipient date of birth (YYYY-MM-DD) if shown",
        "income_code": "Income code shown on the form",
        "gross_income": "Gross income amount (number only)",
        "federal_tax_withheld": "Federal tax withheld amount (number only)",
        "withholding_agent_name": "Name of the withholding agent",
    },
    "lease": {
        "lease_type": "Lease type such as lease or sublease",
        "landlord_name": "Landlord, owner, or sublessor name",
        "tenant_names": "Names of the tenant or sublessee parties",
        "property_address": "Full property address including unit if visible",
        "lease_start_date": "Lease or sublease start date (YYYY-MM-DD)",
        "lease_end_date": "Lease or sublease end date (YYYY-MM-DD)",
        "monthly_rent": "Monthly rent amount (number only)",
        "security_deposit": "Security deposit amount (number only)",
    },
    "insurance_policy": {
        "carrier_name": "Insurance carrier or provider name",
        "insured_name": "Name of the insured member",
        "membership_id": "Membership, policy, or member ID",
        "policy_start_date": "Policy or coverage start date (YYYY-MM-DD)",
        "policy_end_date": "Policy end date (YYYY-MM-DD) if visible",
        "deductible": "Deductible amount (number only) if visible",
        "support_phone": "Support or claims phone number if visible",
    },
    "health_coverage_application": {
        "applicant_name": "Primary applicant full name",
        "application_date": "Application date (YYYY-MM-DD)",
        "date_of_birth": "Applicant date of birth (YYYY-MM-DD)",
        "phone_number": "Primary phone number",
        "email": "Email address",
        "street_address": "Street address",
        "city": "City",
        "state": "State abbreviation",
        "zip_code": "ZIP code",
        "county": "County if visible",
        "subsidy_requested": "Whether the applicant requested free or low cost coverage / subsidy (true/false)",
    },
    "ein_application": {
        "legal_name": "Legal entity name shown in the EIN application",
        "organization_type": "Organization type, such as LLC",
        "filing_state": "State or territory where the entity is or will be filed",
        "start_date": "Business start date (YYYY-MM-DD)",
        "physical_address": "Physical location address",
        "phone_number": "Business phone number",
        "responsible_party_name": "Responsible party name",
    },
    "paystub": {
        "employee_name": "Employee full name",
        "employer_name": "Employer or PEO name",
        "pay_period_start": "Pay period start date (YYYY-MM-DD)",
        "pay_period_end": "Pay period end date (YYYY-MM-DD)",
        "pay_date": "Pay date or check date (YYYY-MM-DD)",
        "gross_pay": "Gross pay amount (number only)",
        "net_pay": "Net pay amount (number only)",
        "ytd_gross_pay": "Year-to-date gross pay amount if visible (number only)",
    },
    "i9": {
        "employee_name": "Employee full name",
        "employee_first_day_of_employment": "Employee's first day of employment (YYYY-MM-DD)",
        "citizenship_status": "Citizenship or immigration status selected on the form",
        "document_title": "Primary document title entered in Supplement B if visible",
        "issuing_authority": "Issuing authority for the document if visible",
        "document_number": "Document number if visible",
        "document_expiration_date": "Document expiration date (YYYY-MM-DD) if visible",
    },
    "e_verify_case": {
        "case_number": "E-Verify case number",
        "report_prepared_date": "Report prepared date (YYYY-MM-DD)",
        "company_name": "Employer or company name",
        "employee_name": "Employee full name",
        "employee_first_day_of_employment": "Employee's first day of employment (YYYY-MM-DD)",
        "citizenship_status": "Citizenship status listed in the report",
        "document_description": "Document description listed in the report",
        "case_status": "Case result or status if visible",
    },
    "i765": {
        "applicant_name": "Applicant full name",
        "eligibility_category": "Eligibility category or requested authorization category",
        "application_reason": "Reason for applying such as initial permission or renewal",
        "mailing_address": "Mailing address",
        "date_of_birth": "Applicant date of birth (YYYY-MM-DD)",
        "country_of_citizenship": "Country of citizenship or nationality",
        "a_number": "A-Number if visible",
        "uscis_online_account_number": "USCIS online account number if visible",
    },
    "h1b_registration": {
        "registration_number": "USCIS H-1B registration number",
        "employer_name": "Business or organization name",
        "employer_ein": "Employer identification number (format: XX-XXXXXXX or digits only if OCR merged it)",
        "employer_address": "Primary U.S. office or mailing address",
        "authorized_individual_name": "Authorized individual current legal name",
        "authorized_individual_title": "Authorized individual position or title at the business",
    },
    "h1b_status_summary": {
        "status_title": "Main title of the summary, such as H-1B Status",
        "registration_window_start_date": "USCIS H-1B registration opening date (YYYY-MM-DD) if stated",
        "registration_window_end_date": "USCIS H-1B registration closing date (YYYY-MM-DD) if stated",
        "petition_filing_window_start_date": "Full petition filing period start date (YYYY-MM-DD) if stated",
        "petition_filing_window_end_date": "Full petition filing period end date (YYYY-MM-DD) if stated",
        "employment_start_date": "Expected H-1B employment start date (YYYY-MM-DD) if stated",
        "law_firm_name": "Law firm or preparer organization name if visible",
    },
}


def extract_pdf_text(file_path: str | Path) -> str:
    """Backward-compatible text-only wrapper around the richer extraction result."""
    return extract_pdf_text_with_provenance(file_path).text


def extract_pdf_text_with_provenance(file_path: str | Path) -> TextExtractionResult:
    """Extract text from a PDF file.
    Uses Mistral OCR if API key is available (best quality),
    falls back to PyMuPDF (free, local).
    """
    mistral_key = os.environ.get("MISTRAL_API_KEY")

    if mistral_key:
        try:
            text, metadata = _extract_with_mistral_ocr(str(file_path), mistral_key)
            return TextExtractionResult(text=text, engine="mistral_ocr", metadata=metadata)
        except Exception as exc:
            logger.warning("Mistral OCR failed for %s: %s", file_path, exc)

    # Fallback: PyMuPDF local extraction
    doc = fitz.open(str(file_path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    page_count = len(doc)
    doc.close()
    return TextExtractionResult(
        text="\n".join(text_parts),
        engine="pymupdf",
        metadata={"page_count": page_count, "source": "pymupdf"},
    )


def _build_mistral_client(api_key: str):
    """Create a Mistral client compatible with the installed SDK layout."""
    try:
        module = importlib.import_module("mistralai.client")
        mistral_cls = getattr(module, "Mistral")
    except (ImportError, AttributeError):
        module = importlib.import_module("mistralai")
        mistral_cls = getattr(module, "Mistral")
    return mistral_cls(api_key=api_key)


def _extract_with_mistral_ocr(file_path: str, api_key: str) -> tuple[str, dict[str, Any]]:
    """Use Mistral OCR API for high-quality document parsing."""
    import base64

    client = _build_mistral_client(api_key)

    # Read file and encode as base64 data URI
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # Determine MIME type
    if file_path.lower().endswith(".pdf"):
        mime = "application/pdf"
    elif file_path.lower().endswith(".png"):
        mime = "image/png"
    elif file_path.lower().endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    else:
        mime = "application/octet-stream"

    b64 = base64.b64encode(file_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"

    # Call Mistral OCR
    if mime == "application/pdf":
        result = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": data_uri},
        )
    else:
        result = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": data_uri},
        )

    # Extract text from all pages
    text_parts = []
    for page in result.pages:
        text_parts.append(page.markdown)

    return "\n\n".join(text_parts), {
        "page_count": len(result.pages),
        "model": "mistral-ocr-latest",
        "source": "mistral",
    }


def extract_supporting_excerpt(text: str, value: Any, window: int = 160) -> str | None:
    """Return a short excerpt around an extracted value when possible."""
    if value in (None, ""):
        return None

    needle = str(value).strip()
    if not needle:
        return None

    lower_text = text.lower()
    lower_needle = needle.lower()
    idx = lower_text.find(lower_needle)
    if idx == -1:
        return None

    start = max(0, idx - window)
    end = min(len(text), idx + len(needle) + window)
    return text[start:end].strip()


def _normalize_iso_date_value(value: Any) -> str | None:
    if value in (None, ""):
        return None

    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        try:
            return datetime.strptime(digits, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _normalize_numeric_value(value: Any, *, fixed_decimals: int | None = None) -> str | None:
    if value in (None, ""):
        return None

    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    raw = raw.strip("()")
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    normalized = match.group(0)
    if fixed_decimals is None:
        return normalized

    try:
        quantized = Decimal(normalized).quantize(Decimal(f"1.{'0' * fixed_decimals}"))
    except InvalidOperation:
        return normalized
    return f"{quantized:.{fixed_decimals}f}"


def _embedded_birthdate_from_long_id(text: str) -> str | None:
    for match in re.findall(r"\b\d{17}[0-9Xx]\b", text):
        candidate = _normalize_iso_date_value(match[6:14])
        if candidate:
            return candidate
    return None


def _extract_1042s_birthdate(text: str) -> str | None:
    label_match = re.search(r"13l Recipient'?s date of birth", text, re.IGNORECASE)
    if label_match:
        snippet = text[label_match.start():label_match.start() + 500]
        snippet = re.split(r"14a|Tax withheld by other agents", snippet, flags=re.IGNORECASE)[0]
        separated_match = re.search(r"((?:\d\s*\|\s*){8})", snippet)
        if separated_match:
            digits = re.sub(r"\D", "", separated_match.group(1))
            normalized = _normalize_iso_date_value(digits)
            if normalized:
                return normalized

    return _embedded_birthdate_from_long_id(text)


def _extract_1042s_account_number(text: str) -> str | None:
    match = re.search(
        r"13k Recipient'?s account number[^A-Z0-9]*([A-Z0-9-]{4,})",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return None


def _extract_1042s_income_code(text: str) -> str | None:
    match = re.search(r"\b1 Income code\b[^0-9]{0,20}(\d{1,2})", text, re.IGNORECASE)
    if match:
        return match.group(1).zfill(2)
    return None


def _extract_1042s_box_amount(text: str, label: str) -> str | None:
    match = re.search(
        rf"{re.escape(label)}[^0-9(]{{0,40}}\(?([0-9]+(?:\.[0-9]+)?)\)?",
        text,
        re.IGNORECASE,
    )
    if match:
        return _normalize_numeric_value(match.group(1), fixed_decimals=2)
    return None


def _normalize_1042s_result(text: str, result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)

    birthdate = _extract_1042s_birthdate(text)
    if birthdate:
        normalized["date_of_birth"] = birthdate
    else:
        normalized["date_of_birth"] = _normalize_iso_date_value(normalized.get("date_of_birth"))

    account_number = _extract_1042s_account_number(text)
    if account_number:
        normalized["recipient_account_number"] = account_number

    income_code = _extract_1042s_income_code(text)
    if income_code:
        normalized["income_code"] = income_code

    gross_income = _extract_1042s_box_amount(text, "2 Gross income")
    if gross_income is not None:
        normalized["gross_income"] = gross_income
    else:
        normalized["gross_income"] = _normalize_numeric_value(
            normalized.get("gross_income"),
            fixed_decimals=2,
        )

    federal_tax_withheld = _extract_1042s_box_amount(text, "7a Federal tax withheld")
    if federal_tax_withheld is not None:
        normalized["federal_tax_withheld"] = federal_tax_withheld
    else:
        normalized["federal_tax_withheld"] = _normalize_numeric_value(
            normalized.get("federal_tax_withheld"),
            fixed_decimals=2,
        )

    tax_year = normalized.get("tax_year")
    if tax_year not in (None, ""):
        year_match = re.search(r"(20\d{2}|19\d{2})", str(tax_year))
        if year_match:
            normalized["tax_year"] = int(year_match.group(1))

    return normalized


def _normalize_selected_fields(
    result: dict[str, Any],
    *,
    date_fields: tuple[str, ...] = (),
    numeric_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    normalized = dict(result)
    for field_name in date_fields:
        normalized[field_name] = _normalize_iso_date_value(normalized.get(field_name))
    for field_name in numeric_fields:
        normalized[field_name] = _normalize_numeric_value(
            normalized.get(field_name),
            fixed_decimals=2,
        )
    return normalized


def _normalize_result(doc_type: str, text: str, result: dict[str, Any]) -> dict[str, Any]:
    if doc_type == "1042s":
        return _normalize_1042s_result(text, result)
    if doc_type == "paystub":
        return _normalize_selected_fields(
            result,
            date_fields=("pay_period_start", "pay_period_end", "pay_date"),
            numeric_fields=("gross_pay", "net_pay", "ytd_gross_pay"),
        )
    if doc_type == "i9":
        return _normalize_selected_fields(
            result,
            date_fields=("employee_first_day_of_employment", "document_expiration_date"),
        )
    if doc_type == "e_verify_case":
        return _normalize_selected_fields(
            result,
            date_fields=("report_prepared_date", "employee_first_day_of_employment"),
        )
    if doc_type == "i765":
        return _normalize_selected_fields(result, date_fields=("date_of_birth",))
    if doc_type == "h1b_status_summary":
        return _normalize_selected_fields(
            result,
            date_fields=(
                "registration_window_start_date",
                "registration_window_end_date",
                "petition_filing_window_start_date",
                "petition_filing_window_end_date",
                "employment_start_date",
            ),
        )
    return result


def extract_document(
    doc_type: str,
    text: str,
) -> dict[str, dict[str, Any]]:
    """Extract structured fields from document text using LLM.

    Returns dict of {field_name: {"value": ..., "confidence": ...}}
    """
    schema = SCHEMAS.get(doc_type, {})
    if not schema:
        return {}

    result = _normalize_result(doc_type, text, _call_llm(text, doc_type, schema))

    # Map to {field_name: {"value": ..., "confidence": ...}}
    fields: dict[str, dict[str, Any]] = {}
    for field_name in schema:
        value = result.get(field_name)
        confidence = 0.85 if value is not None else 0.0
        fields[field_name] = {"value": value, "confidence": confidence}

    return fields


def _call_llm(
    text: str,
    doc_type: str,
    schema: dict[str, str],
) -> dict[str, Any]:
    """Call LLM to extract structured fields from document text.
    Provider selection is shared with chat via the LLM runtime configuration.
    """
    field_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in schema.items())

    prompt = f"""Extract the following fields from this {doc_type} document.
Return a JSON object with these fields. Use null for any field you cannot find.

Fields to extract:
{field_descriptions}

Document text:
{text}

Return ONLY valid JSON, no explanation."""
    return extract_json(
        system_prompt="You are a document field extractor. Return only valid JSON, no explanation or markdown.",
        user_prompt=prompt,
        temperature=0,
        max_tokens=4096,
    )
