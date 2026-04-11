"""Tests for Form 8843 generation."""

from __future__ import annotations

import fitz


def test_defaults_excludable_days_for_standard_f1_student_case():
    from compliance_os.web.services.form_8843 import _resolve_days_excludable_current

    assert _resolve_days_excludable_current(
        {
            "visa_type": "F-1",
            "arrival_date": "2023-10-22",
            "days_present_current": 365,
            "days_excludable_current": None,
            "changed_status": False,
            "applied_for_residency": False,
        }
    ) == 365


def test_preserves_explicit_excludable_days_override():
    from compliance_os.web.services.form_8843 import _resolve_days_excludable_current

    assert _resolve_days_excludable_current(
        {
            "visa_type": "F-1",
            "arrival_date": "2023-10-22",
            "days_present_current": 365,
            "days_excludable_current": 120,
            "changed_status": False,
            "applied_for_residency": False,
        }
    ) == 120


def test_generate_form_8843_pdf():
    from compliance_os.web.services.form_8843 import generate_form_8843

    pdf_bytes = generate_form_8843(
        {
            "full_name": "Jessica Chen",
            "email": "jessica@example.com",
            "visa_type": "F-1",
            "country_citizenship": "China",
            "country_passport": "China",
            "passport_number": "E12345678",
            "school_name": "Columbia University",
            "school_address": "New York, NY 10027",
            "days_present_current": 340,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
        }
    )

    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_one = doc[0]
    page_one_text = page_one.get_text("text")
    text = "\n".join(page.get_text("text") for page in doc)
    assert "Jessica" in page_one_text
    assert "F-1" in page_one_text
    assert "China" in page_one_text
    assert "340" in page_one_text
    assert "Jessica Chen" in text
    assert "Columbia University" in text
    assert "China" in text
    assert "340" in text
