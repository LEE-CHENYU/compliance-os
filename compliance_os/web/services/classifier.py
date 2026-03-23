"""Lightweight document classification using regex pattern matching."""

import re
from dataclasses import dataclass


@dataclass
class Classification:
    doc_type: str | None
    confidence: str | None  # "high" or None


PATTERNS: dict[str, list[str]] = {
    "w2": [r"Wage and Tax Statement", r"Form W-2"],
    "1040nr": [r"Nonresident Alien Income Tax Return", r"Form 1040-NR"],
    "1040": [r"U\.S\. Individual Income Tax Return", r"Form 1040(?!-NR)\b"],
    "i20": [r"Certificate of Eligibility", r"Form I-20"],
    "i94": [r"Arrival/Departure Record", r"I-94"],
    "ein_letter": [r"Employer Identification Number", r"EIN.*assigned"],
    "passport": [r"PASSPORT", r"PASSEPORT"],
    "1099": [r"Form 1099", r"Miscellaneous Income"],
}


def classify_text(text: str) -> Classification:
    """Classify document based on extracted text content."""
    for doc_type, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Classification(doc_type=doc_type, confidence="high")
    return Classification(doc_type=None, confidence=None)


def classify_file(file_path: str, mime_type: str) -> Classification:
    """Classify a file by extracting text and matching patterns."""
    if mime_type == "application/pdf":
        from compliance_os.web.services.pdf_reader import extract_first_page
        text = extract_first_page(file_path)
        if text:
            return classify_text(text)
    return Classification(doc_type=None, confidence=None)
