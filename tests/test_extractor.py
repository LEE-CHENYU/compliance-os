"""Tests for LLM extraction service (mocked OpenAI)."""
import json
import pytest
from unittest.mock import patch, MagicMock
from compliance_os.web.services.extractor import extract_document, SCHEMAS, extract_pdf_text


def test_schemas_defined():
    assert "i983" in SCHEMAS
    assert "employment_letter" in SCHEMAS
    assert "tax_return" in SCHEMAS
    assert "job_title" in SCHEMAS["i983"]
    assert "employer_name" in SCHEMAS["employment_letter"]
    assert "form_type" in SCHEMAS["tax_return"]


def test_extract_returns_fields():
    mock_result = {
        "job_title": "Data Analyst",
        "employer_name": "Acme Corp",
        "start_date": "2025-07-01",
        "compensation": 85000,
        "sevis_number": "N0012345678",
        "major": "Computer Science",
    }
    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_result):
        fields = extract_document("i983", "Sample text about Data Analyst at Acme Corp")
        assert fields["job_title"]["value"] == "Data Analyst"
        assert fields["employer_name"]["value"] == "Acme Corp"
        assert fields["start_date"]["value"] == "2025-07-01"


def test_extract_missing_fields_are_none():
    mock_result = {"job_title": "Data Analyst"}
    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_result):
        fields = extract_document("i983", "Minimal text")
        assert fields["job_title"]["value"] == "Data Analyst"
        assert fields["employer_name"]["value"] is None


def test_extract_employment_letter():
    mock_result = {
        "job_title": "Business Operations Associate",
        "employer_name": "Acme Corp",
        "work_location": "New York, NY",
        "compensation": 85000,
    }
    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_result):
        fields = extract_document("employment_letter", "Dear candidate, we are pleased to offer...")
        assert fields["job_title"]["value"] == "Business Operations Associate"
        assert fields["work_location"]["value"] == "New York, NY"


def test_extract_tax_return():
    mock_result = {
        "form_type": "1040-NR",
        "tax_year": 2024,
        "schedules_present": ["schedule_d"],
        "form_5472_present": False,
    }
    with patch("compliance_os.web.services.extractor._call_openai", return_value=mock_result):
        fields = extract_document("tax_return", "Form 1040-NR for tax year 2024")
        assert fields["form_type"]["value"] == "1040-NR"
        assert fields["form_5472_present"]["value"] is False
