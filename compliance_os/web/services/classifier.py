"""Lightweight document classification using regex pattern matching."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Classification:
    doc_type: str | None
    confidence: str | None  # "high" or None
    source: str | None = None


AUTO_DOC_TYPE_VALUES = {"", "auto", "autodetect", "detect", "unknown"}


FILENAME_PATTERNS: dict[str, list[str]] = {
    "articles_of_organization": [r"articles?[_ -]?of[_ -]?organization"],
    "certificate_of_good_standing": [
        r"cert(?:ificate)?[_ -]?of[_ -]?good[_ -]?standing",
        r"good[_ -]?standing",
    ],
    "registered_agent_consent": [
        r"consent[_ -]?to[_ -]?appointment[_ -]?by[_ -]?registered[_ -]?agent",
        r"registered[_ -]?agent[_ -]?consent",
    ],
    "i983": [r"(?:^|[^a-z0-9])i-?983(?:[^a-z0-9]|$)", r"training[_ -]?plan"],
    "employment_letter": [r"employment[_ -]?letter", r"offer[_ -]?letter", r"employment[_ -]?offer"],
    "i20": [r"(?:^|[^a-z0-9])i-?20(?:[^a-z0-9]|$)"],
    "i94": [r"(?:^|[^a-z0-9])i-?94(?:[^a-z0-9]|$)"],
    "ead": [r"(?:^|[^a-z0-9])ead(?:[^a-z0-9]|$)", r"employment[_ -]?authorization"],
    "ein_letter": [r"\bcp[_ -]?575\b", r"\bein\b"],
    "ein_application": [r"\bein[_ -]?(?:individual[_ -]?request|application)\b"],
    "w2": [r"(?:^|[^a-z0-9])w-?2(?:[^a-z0-9]|$)"],
    "passport": [r"(?:^|[^a-z0-9])passport(?:[^a-z0-9]|$)"],
    "1042s": [r"(?:^|[^a-z0-9])1042-?s(?:[^a-z0-9]|$)"],
    "tax_return": [r"tax[_ -]?return", r"(?:^|[^a-z0-9])1040(?:-nr)?(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])1120(?:-s)?(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])1065(?:[^a-z0-9]|$)"],
    "1099": [r"(?:^|[^a-z0-9])1099(?:[^a-z0-9]|$)"],
    "lease": [r"(?:^|[^a-z0-9])sublease(?:[^a-z0-9]|$)", r"(?:^|[^a-z0-9])lease(?:[^a-z0-9]|$)"],
    "insurance_policy": [r"nomad[_ -]?insurance", r"(?:^|[^a-z0-9])insurance(?:[^a-z0-9]|$)"],
    "paystub": [r"(?:^|[^a-z0-9])pay[_ -]?stub(?:[^a-z0-9]|$)", r"paystubs?"],
    "i9": [r"(?:^|[^a-z0-9])i[_ -]?9(?:[^a-z0-9]|$)"],
    "e_verify_case": [r"e[_ -]?verify", r"everify"],
    "i765": [r"(?:^|[^a-z0-9])i[_ -]?765(?:[^a-z0-9]|$)"],
    "h1b_registration": [r"h[_ -]?1b[_ -]?r", r"h[_ -]?1b[_ -]?registration", r"uscis[_ -]?h[_ -]?1b[_ -]?registration"],
    "h1b_status_summary": [r"h[_ -]?1b[_ -]?status[_ -]?overview", r"h[_ -]?1b[_ -]?status[_ -]?summary"],
}


PATTERNS: dict[str, list[str]] = {
    "articles_of_organization": [
        r"Articles of Organization",
        r"Limited Liability Company Articles of Organization",
        r"The name of the limited liability company is",
    ],
    "certificate_of_good_standing": [
        r"good standing",
        r"Secretary of State",
        r"entity identification number",
    ],
    "registered_agent_consent": [
        r"Consent to Appointment by Registered Agent",
        r"registered agent",
        r"voluntarily consent to serve",
    ],
    "i983": [
        r"TRAINING PLAN FOR STEM OPT STUDENTS",
        r"Form I-983",
        r"STEM Optional Practical Training",
    ],
    "i20": [
        r"Certificate of Eligibility for Nonimmigrant Student Status",
        r"Form I-20",
        r"1-20,\s*Certificate of Eligibility",
    ],
    "i94": [
        r"Arrival\s*/\s*Departure\s*Record",
        r"Most Recent I-94",
        r"Class of Admission",
        r"Admit Until Date",
    ],
    "ead": [
        r"Employment Authorization Document",
        r"CARD EXPIRES",
        r"USCIS#",
    ],
    "passport": [r"\bPASSPORT\b", r"PASSEPORT", r"Nationality", r"P<[A-Z]{3}"],
    "ein_letter": [r"Employer Identification Number", r"EIN.*assigned", r"CP\s*575"],
    "ein_application": [
        r"receive your EIN",
        r"Summary of your information",
        r"Organization Type:\s*LLC",
    ],
    "w2": [r"Wage and Tax Statement", r"Form W-2"],
    "1042s": [
        r"Form 1042-S",
        r"withholding agent",
        r"federal tax withheld",
        r"recipient's account number",
    ],
    "tax_return": [
        r"Nonresident Alien Income Tax Return",
        r"U\.S\. Individual Income Tax Return",
        r"Form 1040(?!-NR)\b",
        r"Form 1040-NR",
        r"Form 1120-S",
        r"Form 1120\b",
        r"Form 1065",
    ],
    "1099": [r"Form 1099", r"Miscellaneous Income"],
    "employment_letter": [
        r"Employment Offer Letter",
        r"Offer Letter",
        r"pleased to offer you",
        r"pleased to offer you the position of",
        r"employment at will",
    ],
    "lease": [
        r"Sublease Agreement",
        r"\bThis lease\b",
        r"Tenant and Owner",
        r"Premises:",
    ],
    "insurance_policy": [
        r"Nomad Insurance",
        r"Membership ID",
        r"not a guarantee of coverage",
    ],
    "health_coverage_application": [
        r"CoveredCA\.com",
        r"Application date",
        r"Primary Contact for your household",
    ],
    "paystub": [
        r"Pay Period Start",
        r"Pay Period End",
        r"Pay Date",
        r"Net Pay",
    ],
    "i9": [
        r"Employment Eligibility Verification",
        r"Form I-9",
        r"U\.S\. Citizenship and Immigration Services",
    ],
    "e_verify_case": [
        r"E-Verify Case Number",
        r"Company Information",
        r"Employee Information",
        r"Case Result",
    ],
    "i765": [
        r"Application For Employment Authorization",
        r"Form I-765",
        r"USCIS Form I-765",
    ],
    "h1b_registration": [
        r"USCIS H-1B Registration",
        r"Registration Number",
        r"What is your business or organization name\?",
    ],
    "h1b_status_summary": [
        r"H[- ]?1B Status",
        r"Requirements for H[- ]?1B visa status",
        r"How to File for New H[- ]?1B visa status",
        r"Required Documents for Filing for H[- ]?1B visa status",
    ],
}


TEXT_MIN_MATCHES: dict[str, int] = {
    "articles_of_organization": 2,
    "certificate_of_good_standing": 2,
    "registered_agent_consent": 2,
    "i983": 2,
    "employment_letter": 2,
    "i20": 2,
    "i94": 2,
    "ead": 2,
    "passport": 2,
    "ein_letter": 2,
    "ein_application": 2,
    "w2": 2,
    "1042s": 2,
    "tax_return": 2,
    "1099": 2,
    "lease": 2,
    "insurance_policy": 2,
    "health_coverage_application": 2,
    "paystub": 2,
    "i9": 2,
    "e_verify_case": 2,
    "i765": 2,
    "h1b_registration": 2,
    "h1b_status_summary": 2,
}

OCR_TEXT_MIN_MATCH_OVERRIDES: dict[str, int] = {
    # OCR on unsupported forms can mention these identifiers incidentally.
    # Raise the bar only for OCR fallback to avoid false-positive intake routing.
    "i94": 3,
    "passport": 3,
    "ein_letter": 3,
}

OCR_REQUIRED_ANY_PATTERNS: dict[str, list[str]] = {
    # Require a strong anchor for high-risk OCR classifications.
    "i94": [r"Arrival\s*/\s*Departure\s*Record"],
    "ein_letter": [r"CP\s*575"],
}


DOC_TYPE_ALIASES: dict[str, str] = {
    "1042_s": "1042s",
    "1042s": "1042s",
    "articles_of_organization": "articles_of_organization",
    "certificate_of_good_standing": "certificate_of_good_standing",
    "cp_575": "ein_letter",
    "ead": "ead",
    "ein_application": "ein_application",
    "ein_letter": "ein_letter",
    "employment_letter": "employment_letter",
    "employment_offer": "employment_letter",
    "employment_offer_letter": "employment_letter",
    "good_standing_certificate": "certificate_of_good_standing",
    "health_coverage_application": "health_coverage_application",
    "i20": "i20",
    "i_20": "i20",
    "i94": "i94",
    "i_94": "i94",
    "i983": "i983",
    "i_983": "i983",
    "insurance_policy": "insurance_policy",
    "i9": "i9",
    "i_9": "i9",
    "i765": "i765",
    "i_765": "i765",
    "lease": "lease",
    "offer_letter": "employment_letter",
    "passport": "passport",
    "paystub": "paystub",
    "pay_stub": "paystub",
    "registered_agent_consent": "registered_agent_consent",
    "tax_return": "tax_return",
    "e_verify": "e_verify_case",
    "e_verify_case": "e_verify_case",
    "everify": "e_verify_case",
    "h1b_registration": "h1b_registration",
    "h_1b_registration": "h1b_registration",
    "h1b_status_summary": "h1b_status_summary",
    "h_1b_status_summary": "h1b_status_summary",
    "h1b_status_overview": "h1b_status_summary",
    "h_1b_status_overview": "h1b_status_summary",
    "1099": "1099",
    "w2": "w2",
    "w_2": "w2",
}

SUPPORTED_DOC_TYPES = set(FILENAME_PATTERNS) | set(PATTERNS)


def is_auto_doc_type(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in AUTO_DOC_TYPE_VALUES


def normalize_doc_type(value: str | None) -> str | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw or is_auto_doc_type(raw):
        return None

    key = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    alias = DOC_TYPE_ALIASES.get(key, key)
    return alias if alias in SUPPORTED_DOC_TYPES else None


def _pattern_scores(text: str, pattern_map: dict[str, list[str]]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for doc_type, patterns in pattern_map.items():
        score = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
        if score:
            scores[doc_type] = score
    return scores


def _best_scored_match(
    text: str,
    pattern_map: dict[str, list[str]],
    *,
    min_matches: dict[str, int] | None = None,
    required_any_patterns: dict[str, list[str]] | None = None,
    source: str | None = None,
) -> Classification:
    scores = _pattern_scores(text, pattern_map)
    if not scores:
        return Classification(doc_type=None, confidence=None)

    best_score = max(scores.values())
    winners = [doc_type for doc_type, score in scores.items() if score == best_score]
    if len(winners) != 1:
        return Classification(doc_type=None, confidence=None)

    best_doc_type = winners[0]
    required_matches = (min_matches or {}).get(best_doc_type, 1)
    if best_score < required_matches:
        return Classification(doc_type=None, confidence=None)
    required_patterns = (required_any_patterns or {}).get(best_doc_type)
    if required_patterns and not any(re.search(pattern, text, re.IGNORECASE) for pattern in required_patterns):
        return Classification(doc_type=None, confidence=None)
    return Classification(doc_type=best_doc_type, confidence="high", source=source)


def classify_text(
    text: str,
    *,
    min_matches: dict[str, int] | None = None,
    required_any_patterns: dict[str, list[str]] | None = None,
) -> Classification:
    """Classify document based on extracted text content.

    Text classification is conservative on purpose. Unsupported documents often
    mention identifiers like I-94, passport, or EIN as references, so a single
    incidental match should not drive a classification decision.
    """
    effective_min_matches = dict(TEXT_MIN_MATCHES)
    if min_matches:
        effective_min_matches.update(min_matches)
    return _best_scored_match(
        text,
        PATTERNS,
        min_matches=effective_min_matches,
        required_any_patterns=required_any_patterns,
        source="text",
    )


def classify_filename(file_path: str) -> Classification:
    """Classify a document using only its filename."""
    filename = Path(file_path).name.lower()
    return _best_scored_match(filename, FILENAME_PATTERNS, source="filename")


def classify_file(file_path: str, mime_type: str, *, allow_ocr: bool = True) -> Classification:
    """Classify a file by filename, local text extraction, then optional OCR fallback."""
    by_name = classify_filename(file_path)
    if by_name.doc_type:
        return by_name

    if mime_type == "application/pdf":
        from compliance_os.web.services.pdf_reader import extract_first_page

        text = extract_first_page(file_path)
        if text:
            by_text = classify_text(text)
            if by_text.doc_type:
                return by_text

    if allow_ocr and mime_type in {"application/pdf", "image/png", "image/jpeg"}:
        from compliance_os.web.services.extractor import extract_pdf_text

        text = extract_pdf_text(file_path)
        if text:
            by_ocr = classify_text(
                text,
                min_matches=OCR_TEXT_MIN_MATCH_OVERRIDES,
                required_any_patterns=OCR_REQUIRED_ANY_PATTERNS,
            )
            if by_ocr.doc_type:
                by_ocr.source = "ocr"
                return by_ocr

    return Classification(doc_type=None, confidence=None)
