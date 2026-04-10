"""Tests for Form 8843 generation."""

from __future__ import annotations

import fitz


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
    text = "\n".join(page.get_text("text") for page in doc)
    assert "Jessica Chen" in text
    assert "Columbia University" in text
    assert "China" in text
    assert "340" in text

