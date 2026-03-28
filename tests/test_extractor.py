"""Tests for LLM extraction service (mocked OpenAI)."""
from types import SimpleNamespace
from unittest.mock import patch

import compliance_os.web.services.extractor as extractor
from compliance_os.web.services.extractor import SCHEMAS, extract_document


def test_schemas_defined():
    assert "articles_of_organization" in SCHEMAS
    assert "certificate_of_good_standing" in SCHEMAS
    assert "registered_agent_consent" in SCHEMAS
    assert "i983" in SCHEMAS
    assert "employment_letter" in SCHEMAS
    assert "tax_return" in SCHEMAS
    assert "i94" in SCHEMAS
    assert "ead" in SCHEMAS
    assert "w2" in SCHEMAS
    assert "ein_letter" in SCHEMAS
    assert "passport" in SCHEMAS
    assert "1042s" in SCHEMAS
    assert "lease" in SCHEMAS
    assert "insurance_policy" in SCHEMAS
    assert "health_coverage_application" in SCHEMAS
    assert "ein_application" in SCHEMAS
    assert "paystub" in SCHEMAS
    assert "i9" in SCHEMAS
    assert "e_verify_case" in SCHEMAS
    assert "i765" in SCHEMAS
    assert "h1b_registration" in SCHEMAS
    assert "h1b_status_summary" in SCHEMAS
    assert "entity_name" in SCHEMAS["articles_of_organization"]
    assert "standing_status" in SCHEMAS["certificate_of_good_standing"]
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
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("i983", "Sample text about Data Analyst at Acme Corp")
        assert fields["job_title"]["value"] == "Data Analyst"
        assert fields["employer_name"]["value"] == "Acme Corp"
        assert fields["start_date"]["value"] == "2025-07-01"


def test_extract_missing_fields_are_none():
    mock_result = {"job_title": "Data Analyst"}
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
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
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
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
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("tax_return", "Form 1040-NR for tax year 2024")
        assert fields["form_type"]["value"] == "1040-NR"
        assert fields["form_5472_present"]["value"] is False


def test_extract_articles_of_organization():
    mock_result = {
        "entity_name": "Bamboo Shoot Growth Capital LLC",
        "filing_state": "WY",
        "filing_date": "2023-06-16",
        "entity_id": "2023-001286103",
        "registered_agent_name": "Registered Agents Inc",
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("articles_of_organization", "Limited Liability Company Articles of Organization")
        assert fields["entity_name"]["value"] == "Bamboo Shoot Growth Capital LLC"
        assert fields["entity_id"]["value"] == "2023-001286103"


def test_extract_1042s():
    mock_result = {
        "tax_year": 2025,
        "recipient_name": "CHENYU LI",
        "federal_tax_withheld": 0,
        "gross_income": 3,
        "recipient_account_number": "7689-2619",
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("1042s", "Form 1042-S recipient account number 7689-2619")
        assert fields["tax_year"]["value"] == 2025
        assert fields["recipient_name"]["value"] == "CHENYU LI"
        assert fields["recipient_account_number"]["value"] == "7689-2619"
        assert fields["gross_income"]["value"] == "3.00"
        assert fields["federal_tax_withheld"]["value"] == "0.00"


def test_extract_1042s_normalizes_date_of_birth_from_ocr_text():
    text = """
    13i Recipient's foreign tax identification number, if any 320106199809180413
    13k Recipient's account number 7689-2619
    13l Recipient's date of birth (YYYYMMDD)
    | 7c Check if withholding occurred in subsequent year with respect to a partnership interest | ☐ | 1 | 9 | 9 | 8 | 0 | 9 | 1 |
    2 Gross income 3
    7a Federal tax withheld 5.00
    """
    mock_result = {
        "tax_year": "2024",
        "recipient_name": "CHENYU LI",
        "recipient_account_number": None,
        "date_of_birth": "1998-09-01",
        "gross_income": None,
        "federal_tax_withheld": None,
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("1042s", text)
        assert fields["date_of_birth"]["value"] == "1998-09-18"
        assert fields["recipient_account_number"]["value"] == "7689-2619"
        assert fields["gross_income"]["value"] == "3.00"
        assert fields["federal_tax_withheld"]["value"] == "5.00"


def test_extract_paystub_normalizes_dates_and_amounts():
    mock_result = {
        "employee_name": "Chenyu Li",
        "employer_name": "Tiger Cloud LLC",
        "pay_period_start": "01/01/2024",
        "pay_period_end": "01/15/2024",
        "pay_date": "01/12/2024",
        "gross_pay": "3,200",
        "net_pay": "2,456.7",
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("paystub", "Pay Period Start 01/01/2024 Pay Date 01/12/2024")
        assert fields["employee_name"]["value"] == "Chenyu Li"
        assert fields["pay_period_start"]["value"] == "2024-01-01"
        assert fields["pay_period_end"]["value"] == "2024-01-15"
        assert fields["pay_date"]["value"] == "2024-01-12"
        assert fields["gross_pay"]["value"] == "3200.00"
        assert fields["net_pay"]["value"] == "2456.70"


def test_extract_h1b_registration():
    mock_result = {
        "registration_number": "ABC123456789",
        "employer_name": "Bamboo Shoot Growth Capital LLC",
        "employer_ein": "93-1924106",
        "authorized_individual_name": "Chenyu Li",
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("h1b_registration", "USCIS H-1B Registration Registration Number")
        assert fields["registration_number"]["value"] == "ABC123456789"
        assert fields["employer_name"]["value"] == "Bamboo Shoot Growth Capital LLC"
        assert fields["employer_ein"]["value"] == "93-1924106"


def test_extract_h1b_status_summary_normalizes_dates():
    mock_result = {
        "status_title": "H-1B Status",
        "registration_window_start_date": "03/01/2025",
        "registration_window_end_date": "03/20/2025",
        "petition_filing_window_start_date": "04/01/2025",
        "petition_filing_window_end_date": "06/30/2025",
        "employment_start_date": "10/01/2025",
        "law_firm_name": "MT Law",
    }
    with patch("compliance_os.web.services.extractor._call_llm", return_value=mock_result):
        fields = extract_document("h1b_status_summary", "H-1B Status How to File for New H-1B visa status")
        assert fields["status_title"]["value"] == "H-1B Status"
        assert fields["registration_window_start_date"]["value"] == "2025-03-01"
        assert fields["registration_window_end_date"]["value"] == "2025-03-20"
        assert fields["petition_filing_window_start_date"]["value"] == "2025-04-01"
        assert fields["petition_filing_window_end_date"]["value"] == "2025-06-30"
        assert fields["employment_start_date"]["value"] == "2025-10-01"
        assert fields["law_firm_name"]["value"] == "MT Law"


def test_build_mistral_client_prefers_client_module(monkeypatch):
    class FakeMistral:
        def __init__(self, api_key):
            self.api_key = api_key

    def fake_import_module(name: str):
        if name == "mistralai.client":
            return SimpleNamespace(Mistral=FakeMistral)
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(extractor.importlib, "import_module", fake_import_module)

    client = extractor._build_mistral_client("test-key")

    assert isinstance(client, FakeMistral)
    assert client.api_key == "test-key"


def test_build_mistral_client_falls_back_to_top_level(monkeypatch):
    calls: list[str] = []

    class FakeMistral:
        def __init__(self, api_key):
            self.api_key = api_key

    def fake_import_module(name: str):
        calls.append(name)
        if name == "mistralai.client":
            raise ImportError("client module unavailable")
        if name == "mistralai":
            return SimpleNamespace(Mistral=FakeMistral)
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(extractor.importlib, "import_module", fake_import_module)

    client = extractor._build_mistral_client("fallback-key")

    assert calls == ["mistralai.client", "mistralai"]
    assert isinstance(client, FakeMistral)
    assert client.api_key == "fallback-key"
