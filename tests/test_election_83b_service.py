"""Unit tests for process_election_83b covering every verdict path and service-center mapping."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

import compliance_os.web.services.election_83b as election_mod
from compliance_os.web.services.pdf_reader import extract_first_page


def _cover_text(result) -> str:
    return extract_first_page(result["artifacts"][1]["path"])


def _letter_text(result) -> str:
    return extract_first_page(result["artifacts"][0]["path"])


@pytest.fixture(autouse=True)
def _redirect_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(election_mod, "ELECTION_83B_DIR", tmp_path / "83b")
    yield


def _intake(**overrides) -> dict:
    base = {
        "grant_date": (date(2026, 4, 1)).isoformat(),
        "taxpayer_name": "Test User",
        "taxpayer_address": "1 Market St, Palo Alto, CA 94301",
        "company_name": "Acme Startup",
        "property_description": "100,000 shares of restricted common stock",
        "share_count": 100000,
        "fair_market_value_per_share": 0.001,
        "exercise_price_per_share": 0.001,
        "vesting_schedule": "4 years, 1-year cliff",
    }
    base.update(overrides)
    return base


# --- verdict: pass (normal case) ---

def test_normal_case_pass_verdict():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=5)).isoformat())
    result = election_mod.process_election_83b("o1", intake, today=today)
    assert result["verdict"] == "pass"
    assert result["deadline_passed"] is False
    assert result["grant_in_future"] is False
    assert result["filing_deadline"] == (today - timedelta(days=5) + timedelta(days=30)).isoformat()


def test_normal_case_summary_mentions_days_remaining():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=5)).isoformat())
    result = election_mod.process_election_83b("o1a", intake, today=today)
    assert "25 days from today" in result["summary"]


# --- boundary: deadline arithmetic (day 0, 29, 30, 31) ---

def test_day_0_grant_today():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=today.isoformat())
    result = election_mod.process_election_83b("o2", intake, today=today)
    assert result["verdict"] == "pass"
    assert result["filing_deadline"] == (today + timedelta(days=30)).isoformat()


def test_day_29_still_in_window():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=29)).isoformat())
    result = election_mod.process_election_83b("o3", intake, today=today)
    assert result["verdict"] == "pass"
    assert result["deadline_passed"] is False


def test_day_30_exactly_still_pass():
    """Deadline == today: strict-less-than comparison means still pass."""
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=30)).isoformat())
    result = election_mod.process_election_83b("o4", intake, today=today)
    assert result["verdict"] == "pass"
    assert result["deadline_passed"] is False


def test_day_31_one_day_past_blocks():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=31)).isoformat())
    result = election_mod.process_election_83b("o5", intake, today=today)
    assert result["verdict"] == "block"
    assert result["deadline_passed"] is True
    assert result["days_past_deadline"] == 1


# --- verdict: block (deadline passed) ---

def test_late_grant_blocks_with_urgent_summary():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=45)).isoformat())
    result = election_mod.process_election_83b("o6", intake, today=today)
    assert result["verdict"] == "block"
    assert result["deadline_passed"] is True
    assert result["days_past_deadline"] == 15
    assert "URGENT" in result["summary"]
    assert "30-day" in result["summary"]


def test_late_grant_next_steps_advise_advisor_first():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today - timedelta(days=60)).isoformat())
    result = election_mod.process_election_83b("o7", intake, today=today)
    first_step = result["next_steps"][0].lower()
    assert "advisor" in first_step or "do not mail" in first_step


def test_very_old_grant_still_handled():
    """A grant from 2 years ago: verdict is still block, not an exception."""
    today = date(2026, 4, 10)
    intake = _intake(grant_date="2024-01-15")
    result = election_mod.process_election_83b("o8", intake, today=today)
    assert result["verdict"] == "block"
    assert result["deadline_passed"] is True


# --- verdict: block (future grant) ---

def test_future_grant_blocks():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today + timedelta(days=5)).isoformat())
    result = election_mod.process_election_83b("o9", intake, today=today)
    assert result["verdict"] == "block"
    assert result["grant_in_future"] is True
    assert "future" in result["summary"].lower()


def test_far_future_grant_blocks():
    today = date(2026, 4, 10)
    intake = _intake(grant_date=(today + timedelta(days=365)).isoformat())
    result = election_mod.process_election_83b("o10", intake, today=today)
    assert result["verdict"] == "block"
    assert result["grant_in_future"] is True


# --- service center inference ---

def test_service_center_california_is_ogden():
    intake = _intake(taxpayer_address="1 Market St, San Francisco, CA 94103")
    result = election_mod.process_election_83b("o-sc-ca", intake)
    text = _cover_text(result)
    assert "Ogden" in text
    assert "CA" in text


def test_service_center_new_york_is_kansas_city():
    intake = _intake(taxpayer_address="1 Broadway, New York, NY 10004")
    result = election_mod.process_election_83b("o-sc-ny", intake)
    assert "Kansas City" in _cover_text(result)


def test_service_center_texas_is_austin():
    intake = _intake(taxpayer_address="1 Congress Ave, Austin, TX 78701")
    result = election_mod.process_election_83b("o-sc-tx", intake)
    assert "Austin" in _cover_text(result)


def test_service_center_florida_is_austin():
    intake = _intake(taxpayer_address="1 Ocean Dr, Miami, FL 33139")
    result = election_mod.process_election_83b("o-sc-fl", intake)
    assert "Austin" in _cover_text(result)


def test_service_center_illinois_is_kansas_city():
    intake = _intake(taxpayer_address="1 State St, Chicago, IL 60601")
    result = election_mod.process_election_83b("o-sc-il", intake)
    assert "Kansas City" in _cover_text(result)


def test_service_center_washington_is_ogden():
    intake = _intake(taxpayer_address="1 Pike St, Seattle, WA 98101")
    result = election_mod.process_election_83b("o-sc-wa", intake)
    assert "Ogden" in _cover_text(result)


def test_service_center_unmapped_territory_falls_back():
    """Puerto Rico (PR) isn't in the individual 1040 mapping — should fall back."""
    intake = _intake(taxpayer_address="1 Main St, San Juan, PR 00901")
    result = election_mod.process_election_83b("o-sc-pr", intake)
    text = _cover_text(result)
    assert "could not infer" in text.lower() or "look up the correct center" in text.lower()


def test_service_center_no_state_in_address_falls_back():
    intake = _intake(taxpayer_address="some freeform address without a state")
    result = election_mod.process_election_83b("o-sc-none", intake)
    text = _cover_text(result)
    assert "could not infer" in text.lower() or "look up the correct center" in text.lower()


# --- output shape ---

def test_result_contains_two_artifacts():
    result = election_mod.process_election_83b("o-shape", _intake())
    labels = {a["label"] for a in result["artifacts"]}
    assert any("election letter" in lbl.lower() for lbl in labels)
    assert any("cover sheet" in lbl.lower() for lbl in labels)


def test_mailing_instructions_differ_for_blocked_case():
    today = date(2026, 4, 10)
    passed = election_mod.process_election_83b("ok", _intake(grant_date=(today - timedelta(days=5)).isoformat()), today=today)
    blocked = election_mod.process_election_83b("blk", _intake(grant_date=(today - timedelta(days=45)).isoformat()), today=today)
    assert passed["mailing_instructions"]["headline"] != blocked["mailing_instructions"]["headline"]
    assert "passed" in blocked["mailing_instructions"]["headline"].lower()


def test_election_letter_includes_grant_details():
    intake = _intake(
        taxpayer_name="Jane Founder",
        company_name="MyCo Inc",
        share_count=50000,
    )
    result = election_mod.process_election_83b("o-letter", intake)
    text = _letter_text(result)
    assert "Jane Founder" in text
    assert "MyCo Inc" in text
    assert "50000" in text


def test_long_hereby_line_wraps_not_truncates():
    """Regression: build_text_pdf used to silently clip long lines.

    Now lines soft-wrap across multiple physical lines so user content
    (company name, property description) remains fully rendered.
    """
    intake = _intake(
        company_name="A Corporation With A Very Long Legal Entity Name",
        property_description="a detailed description of the restricted common stock granted under the plan",
    )
    result = election_mod.process_election_83b("o-wrap", intake)
    text = _letter_text(result)
    assert "A Corporation With A Very Long Legal Entity Name" in text
    assert "detailed description" in text


# --- input validation ---

def test_invalid_date_format_raises():
    intake = _intake(grant_date="not-a-date")
    with pytest.raises(ValueError):
        election_mod.process_election_83b("o-invalid", intake)


def test_missing_required_field_raises():
    intake = _intake()
    del intake["taxpayer_name"]
    with pytest.raises(KeyError):
        election_mod.process_election_83b("o-missing", intake)
