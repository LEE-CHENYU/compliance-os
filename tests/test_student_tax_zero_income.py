"""Zero-income students should be routed to a standalone Form 8843, not a 1040-NR package."""

import compliance_os.web.services.student_tax_check as mod


def _run(monkeypatch, tmp_path, **inputs):
    monkeypatch.setattr(mod, "STUDENT_TAX_DIR", tmp_path / "student_tax")
    base = {
        "tax_year": 2025,
        "full_name": "Test Student",
        "visa_type": "F-1",
        "school_name": "State University",
        "country_citizenship": "India",
    }
    base.update(inputs)
    return mod.process_student_tax_check("test-order", base)


def test_zero_income_routes_to_standalone_june_15(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, wage_income_usd=0, scholarship_income_usd=0, other_income_usd=0)

    assert result["requires_1040nr"] is False
    assert result["filing_deadline"] == "2026-06-15"
    filenames = [a["filename"] for a in result["artifacts"]]
    assert "form-8843.pdf" in filenames
    assert "1040nr-package-summary.pdf" not in filenames


def test_income_keeps_1040nr_package_and_april_15(monkeypatch, tmp_path):
    result = _run(monkeypatch, tmp_path, wage_income_usd=25000)

    assert result["requires_1040nr"] is True
    assert result["filing_deadline"] == "2026-04-15"
    filenames = [a["filename"] for a in result["artifacts"]]
    assert "1040nr-package-summary.pdf" in filenames
    assert "form-8843.pdf" in filenames
