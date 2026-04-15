"""Unit tests for process_student_tax_check — every rule branch + boundary."""
from __future__ import annotations

from pathlib import Path

import pytest

import compliance_os.web.services.student_tax_check as student_tax_mod
from compliance_os.web.services.pdf_reader import extract_first_page


@pytest.fixture(autouse=True)
def _redirect_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(student_tax_mod, "STUDENT_TAX_DIR", tmp_path / "student-tax")
    yield


def _intake(**overrides) -> dict:
    base = {
        "tax_year": 2024,
        "full_name": "Test Student",
        "visa_type": "F-1",
        "school_name": "Stanford University",
        "school_address": "450 Serra Mall, Stanford, CA 94305",
        "school_contact": "ISO",
        "program_director": "Dr. Smith",
        "country_citizenship": "China",
        "country_passport": "China",
        "passport_number": "E12345678",
        "arrival_date": "2022-08-15",
        "days_present_current": 365,
        "days_present_year_1_ago": 365,
        "days_present_year_2_ago": 140,
        "taxpayer_id_number": "123-45-6789",
        "wage_income_usd": 25000,
        "federal_withholding_usd": 2500,
        "state_withholding_usd": 800,
    }
    base.update(overrides)
    return base


def _rule_ids(findings) -> set[str]:
    return {f["rule_id"] for f in findings}


# --- clean / happy-path ---

def test_clean_case_only_info_findings():
    """Default intake is a Chinese F-1 with $25K wages — the China treaty
    auto-suggestion and the FICA exemption reminder fire as informational
    nudges. No critical/warning rules should fire."""
    result = student_tax_mod.process_student_tax_check("clean", _intake())
    rule_ids = _rule_ids(result["findings"])
    assert "student_tax_china_treaty_eligible" in rule_ids
    assert "student_tax_fica_exemption_check" in rule_ids
    # No blockers or warnings
    severities = {f["severity"] for f in result["findings"]}
    assert severities <= {"info"}


def test_clean_case_non_treaty_country_has_only_fica_finding():
    """A Brazilian F-1 student with wages has no auto-treaty. Only FICA reminder fires."""
    intake = _intake(country_citizenship="Brazil", country_passport="Brazil")
    result = student_tax_mod.process_student_tax_check("clean-brazil", intake)
    rule_ids = _rule_ids(result["findings"])
    assert rule_ids == {"student_tax_fica_exemption_check"}


def test_deadline_is_april_15_of_following_year():
    result = student_tax_mod.process_student_tax_check("deadline", _intake(tax_year=2024))
    assert result["filing_deadline"] == "2025-04-15"


def test_default_tax_year_is_prior_year():
    from datetime import date
    intake = _intake()
    del intake["tax_year"]
    result = student_tax_mod.process_student_tax_check("default-year", intake)
    assert result["filing_deadline"] == f"{date.today().year}-04-15"


# --- rule: zero income ---

def test_rule_zero_income_fires_when_total_is_zero():
    intake = _intake(wage_income_usd=0, scholarship_income_usd=0, other_income_usd=0)
    result = student_tax_mod.process_student_tax_check("zero-income", intake)
    assert "student_tax_zero_income" in _rule_ids(result["findings"])


def test_rule_zero_income_does_not_fire_with_scholarship():
    intake = _intake(wage_income_usd=0, scholarship_income_usd=5000)
    result = student_tax_mod.process_student_tax_check("scholarship", intake)
    assert "student_tax_zero_income" not in _rule_ids(result["findings"])


def test_rule_zero_income_does_not_fire_with_other_income():
    intake = _intake(wage_income_usd=0, other_income_usd=1000)
    result = student_tax_mod.process_student_tax_check("other-income", intake)
    assert "student_tax_zero_income" not in _rule_ids(result["findings"])


# --- rule: resident software ---

def test_rule_resident_software_fires():
    intake = _intake(used_resident_software=True)
    result = student_tax_mod.process_student_tax_check("turbotax", intake)
    assert "student_tax_resident_software" in _rule_ids(result["findings"])


def test_rule_resident_software_is_critical_severity():
    """Was 'high' in v1 — aligned to 'critical/warning/info' vocab in batch 3."""
    intake = _intake(used_resident_software=True)
    result = student_tax_mod.process_student_tax_check("vocab", intake)
    rs_finding = next(f for f in result["findings"] if f["rule_id"] == "student_tax_resident_software")
    assert rs_finding["severity"] == "critical"


def test_rule_resident_software_does_not_fire_by_default():
    result = student_tax_mod.process_student_tax_check("no-sw", _intake())
    assert "student_tax_resident_software" not in _rule_ids(result["findings"])


# --- rule: treaty missing country ---

def test_rule_treaty_missing_country_fires():
    intake = _intake(claim_treaty_benefit=True, treaty_country="", treaty_article="21(2)")
    result = student_tax_mod.process_student_tax_check("treaty-no-country", intake)
    assert "student_tax_missing_treaty_country" in _rule_ids(result["findings"])


def test_rule_treaty_missing_country_does_not_fire_when_country_provided():
    intake = _intake(
        claim_treaty_benefit=True,
        treaty_country="China",
        treaty_article="20(c)",
        has_1042s=True,
    )
    result = student_tax_mod.process_student_tax_check("treaty-ok", intake)
    assert "student_tax_missing_treaty_country" not in _rule_ids(result["findings"])


def test_rule_treaty_missing_country_does_not_fire_when_no_treaty_claimed():
    result = student_tax_mod.process_student_tax_check("no-treaty", _intake())
    assert "student_tax_missing_treaty_country" not in _rule_ids(result["findings"])


# --- rule: no withholding ---

def test_rule_no_withholding_fires_when_wages_but_no_fed_tax():
    intake = _intake(wage_income_usd=30000, federal_withholding_usd=0)
    result = student_tax_mod.process_student_tax_check("no-fw", intake)
    assert "student_tax_no_withholding" in _rule_ids(result["findings"])


def test_rule_no_withholding_does_not_fire_without_wages():
    intake = _intake(wage_income_usd=0, scholarship_income_usd=5000, federal_withholding_usd=0)
    result = student_tax_mod.process_student_tax_check("no-wages", intake)
    assert "student_tax_no_withholding" not in _rule_ids(result["findings"])


def test_rule_no_withholding_does_not_fire_when_withholding_present():
    intake = _intake(wage_income_usd=30000, federal_withholding_usd=2500)
    result = student_tax_mod.process_student_tax_check("has-fw", intake)
    assert "student_tax_no_withholding" not in _rule_ids(result["findings"])


# --- rule: missing taxpayer ID (added in batch 3) ---

def test_rule_missing_taxpayer_id_fires():
    intake = _intake(taxpayer_id_number="")
    result = student_tax_mod.process_student_tax_check("no-ssn", intake)
    assert "student_tax_missing_taxpayer_id" in _rule_ids(result["findings"])


def test_rule_missing_taxpayer_id_does_not_fire_when_provided():
    intake = _intake(taxpayer_id_number="123-45-6789")
    result = student_tax_mod.process_student_tax_check("has-ssn", intake)
    assert "student_tax_missing_taxpayer_id" not in _rule_ids(result["findings"])


def test_rule_missing_taxpayer_id_does_not_fire_with_zero_income():
    """Makes no sense to require SSN if we're routing to standalone 8843."""
    intake = _intake(taxpayer_id_number="", wage_income_usd=0, scholarship_income_usd=0, other_income_usd=0)
    result = student_tax_mod.process_student_tax_check("no-ssn-zero", intake)
    assert "student_tax_missing_taxpayer_id" not in _rule_ids(result["findings"])


# --- rule: treaty without 1042-S (added in batch 3) ---

def test_rule_treaty_without_1042s_fires():
    intake = _intake(claim_treaty_benefit=True, treaty_country="China", treaty_article="20(c)", has_1042s=False)
    result = student_tax_mod.process_student_tax_check("no-1042s", intake)
    assert "student_tax_treaty_without_1042s" in _rule_ids(result["findings"])


def test_rule_treaty_without_1042s_does_not_fire_when_has_1042s():
    intake = _intake(claim_treaty_benefit=True, treaty_country="China", treaty_article="20(c)", has_1042s=True)
    result = student_tax_mod.process_student_tax_check("has-1042s", intake)
    assert "student_tax_treaty_without_1042s" not in _rule_ids(result["findings"])


def test_rule_treaty_without_1042s_does_not_fire_when_no_treaty():
    intake = _intake(has_1042s=False)
    result = student_tax_mod.process_student_tax_check("no-treaty-claim", intake)
    assert "student_tax_treaty_without_1042s" not in _rule_ids(result["findings"])


# --- rule: multistate (added in batch 3) ---

def test_rule_multistate_fires_when_states_differ():
    intake = _intake(state_of_residence="NY", state_of_employer="CA")
    result = student_tax_mod.process_student_tax_check("multistate", intake)
    assert "student_tax_multistate_income" in _rule_ids(result["findings"])


def test_rule_multistate_does_not_fire_when_states_match():
    intake = _intake(state_of_residence="CA", state_of_employer="CA")
    result = student_tax_mod.process_student_tax_check("same-state", intake)
    assert "student_tax_multistate_income" not in _rule_ids(result["findings"])


def test_rule_multistate_does_not_fire_when_only_one_state_given():
    intake = _intake(state_of_residence="CA", state_of_employer="")
    result = student_tax_mod.process_student_tax_check("one-state", intake)
    assert "student_tax_multistate_income" not in _rule_ids(result["findings"])


def test_rule_multistate_is_case_insensitive():
    intake = _intake(state_of_residence="ny", state_of_employer="NY")
    result = student_tax_mod.process_student_tax_check("case", intake)
    assert "student_tax_multistate_income" not in _rule_ids(result["findings"])


# --- severity vocabulary alignment (batch 3) ---

def test_all_severities_use_critical_warning_info():
    """Ensure no 'high'/'medium'/'low' slip through after batch 3 alignment."""
    # Trigger every rule
    intake = _intake(
        taxpayer_id_number="",
        wage_income_usd=0, scholarship_income_usd=0, other_income_usd=0,
        used_resident_software=True,
        claim_treaty_benefit=True, treaty_country="", has_1042s=False,
        state_of_residence="NY", state_of_employer="CA",
    )
    result = student_tax_mod.process_student_tax_check("all", intake)
    severities = {f["severity"] for f in result["findings"]}
    assert severities <= {"critical", "warning", "info"}
    assert not severities & {"high", "medium", "low"}


# --- treaty artifact ---

def test_treaty_memo_produced_when_benefit_claimed():
    intake = _intake(
        claim_treaty_benefit=True,
        treaty_country="China",
        treaty_article="20(c)",
        has_1042s=True,
    )
    result = student_tax_mod.process_student_tax_check("treaty-artifact", intake)
    artifact_filenames = {a["filename"] for a in result["artifacts"]}
    assert "treaty-benefit-review-memo.pdf" in artifact_filenames


def test_no_treaty_memo_when_no_benefit():
    result = student_tax_mod.process_student_tax_check("no-treaty-artifact", _intake())
    artifact_filenames = {a["filename"] for a in result["artifacts"]}
    assert "treaty-benefit-review-memo.pdf" not in artifact_filenames


# --- output shape & content ---

def test_result_always_includes_form_8843_and_summary_artifacts():
    result = student_tax_mod.process_student_tax_check("artifacts", _intake())
    labels = [a["filename"] for a in result["artifacts"]]
    assert "form-8843.pdf" in labels
    assert "1040nr-package-summary.pdf" in labels


def test_package_summary_contains_income_breakdown():
    intake = _intake(wage_income_usd=25000, scholarship_income_usd=3000, other_income_usd=500)
    result = student_tax_mod.process_student_tax_check("income-breakdown", intake)
    summary_path = next(a["path"] for a in result["artifacts"] if a["filename"] == "1040nr-package-summary.pdf")
    text = extract_first_page(summary_path)
    assert "$25,000.00" in text
    assert "$3,000.00" in text
    assert "$500.00" in text


def test_total_income_usd_returned_in_result():
    intake = _intake(wage_income_usd=25000, scholarship_income_usd=3000, other_income_usd=500)
    result = student_tax_mod.process_student_tax_check("total", intake)
    assert result["total_income_usd"] == 28500.0


def test_summary_mentions_blocker_count_when_present():
    # Brazil avoids the auto-treaty nudge; resident-software (critical) + FICA (info) fire
    intake = _intake(country_citizenship="Brazil", country_passport="Brazil", used_resident_software=True)
    result = student_tax_mod.process_student_tax_check("count", intake)
    # Critical present → summary uses the blocker framing
    assert "1 blocking issue" in result["summary"]


def test_summary_uses_clean_framing_when_no_blockers():
    # Brazilian F-1 student, no blockers (only FICA info fires) → clean framing
    intake = _intake(country_citizenship="Brazil", country_passport="Brazil")
    result = student_tax_mod.process_student_tax_check("clean-count", intake)
    assert "is ready" in result["summary"]


# --- rule: country treaty auto-suggestion (batch 4) ---

def test_rule_china_treaty_eligible_fires():
    result = student_tax_mod.process_student_tax_check("china-treaty", _intake(country_citizenship="China"))
    assert "student_tax_china_treaty_eligible" in _rule_ids(result["findings"])


def test_rule_china_treaty_does_not_fire_when_user_already_claims():
    intake = _intake(
        country_citizenship="China",
        claim_treaty_benefit=True,
        treaty_country="China",
        treaty_article="20(c)",
        has_1042s=True,
    )
    result = student_tax_mod.process_student_tax_check("china-claimed", intake)
    assert "student_tax_china_treaty_eligible" not in _rule_ids(result["findings"])


def test_rule_india_treaty_eligible_fires():
    intake = _intake(country_citizenship="India", country_passport="India")
    result = student_tax_mod.process_student_tax_check("india-treaty", intake)
    assert "student_tax_india_treaty_eligible" in _rule_ids(result["findings"])


def test_rule_country_treaty_does_not_fire_for_other_countries():
    result = student_tax_mod.process_student_tax_check("france", _intake(country_citizenship="France"))
    assert "student_tax_china_treaty_eligible" not in _rule_ids(result["findings"])
    assert "student_tax_india_treaty_eligible" not in _rule_ids(result["findings"])


def test_rule_country_treaty_does_not_fire_without_wages():
    intake = _intake(
        country_citizenship="China",
        wage_income_usd=0,
        scholarship_income_usd=5000,
    )
    result = student_tax_mod.process_student_tax_check("china-scholarship-only", intake)
    assert "student_tax_china_treaty_eligible" not in _rule_ids(result["findings"])


# --- combinations ---

def test_many_rules_fire_simultaneously():
    intake = _intake(
        taxpayer_id_number="",
        used_resident_software=True,
        claim_treaty_benefit=True,
        treaty_country="",
        wage_income_usd=30000,
        federal_withholding_usd=0,
        state_of_residence="NY",
        state_of_employer="CA",
    )
    result = student_tax_mod.process_student_tax_check("many", intake)
    expected = {
        "student_tax_resident_software",
        "student_tax_missing_treaty_country",
        "student_tax_no_withholding",
        "student_tax_missing_taxpayer_id",
        "student_tax_treaty_without_1042s",
        "student_tax_multistate_income",
    }
    assert expected.issubset(_rule_ids(result["findings"]))


def test_scholarship_only_no_withholding_no_rules_fire():
    """Scholarship-only student (no wages): no withholding rule; no SSN-zero-income either."""
    intake = _intake(
        wage_income_usd=0, scholarship_income_usd=8000, other_income_usd=0,
        federal_withholding_usd=0,
    )
    result = student_tax_mod.process_student_tax_check("scholarship-only", intake)
    assert "student_tax_no_withholding" not in _rule_ids(result["findings"])
    assert "student_tax_zero_income" not in _rule_ids(result["findings"])
