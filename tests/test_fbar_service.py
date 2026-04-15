"""Unit tests for process_fbar_check covering every branch."""
from __future__ import annotations

from datetime import date

import pytest

import compliance_os.web.services.fbar_check as fbar_mod


@pytest.fixture(autouse=True)
def _redirect_fbar_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fbar_mod, "FBAR_CHECK_DIR", tmp_path / "fbar")
    yield


def _account(balance: float, **overrides) -> dict:
    base = {
        "institution_name": "Test Bank",
        "country": "CN",
        "account_type": "savings",
        "account_number_last4": "1234",
        "max_balance_usd": balance,
    }
    base.update(overrides)
    return base


# --- threshold behavior ---

def test_below_threshold_does_not_require():
    result = fbar_mod.process_fbar_check("o1", {"tax_year": 2024, "accounts": [_account(5000)]})
    assert result["requires_fbar"] is False
    assert result["aggregate_max_balance_usd"] == 5000


def test_above_threshold_requires():
    result = fbar_mod.process_fbar_check("o2", {"tax_year": 2024, "accounts": [_account(11000)]})
    assert result["requires_fbar"] is True
    assert result["aggregate_max_balance_usd"] == 11000
    assert "FinCEN" in result["summary"]


def test_boundary_exactly_10000_does_not_require():
    """FinCEN threshold fires when aggregate 'exceeded $10,000' — strictly greater."""
    result = fbar_mod.process_fbar_check("o3", {"tax_year": 2024, "accounts": [_account(10000)]})
    assert result["requires_fbar"] is False


def test_boundary_one_cent_over_requires():
    result = fbar_mod.process_fbar_check("o4", {"tax_year": 2024, "accounts": [_account(10000.01)]})
    assert result["requires_fbar"] is True


def test_fractional_dollars_aggregate_correctly():
    """$9,999.50 + $0.51 = $10,000.01 should require (prior int() truncation bug)."""
    result = fbar_mod.process_fbar_check("o5", {
        "tax_year": 2024,
        "accounts": [_account(9999.50), _account(0.51)],
    })
    assert result["aggregate_max_balance_usd"] == 10000.01
    assert result["requires_fbar"] is True


# --- input shape handling ---

def test_empty_accounts_list_aggregates_to_zero():
    result = fbar_mod.process_fbar_check("o6", {"tax_year": 2024, "accounts": []})
    assert result["aggregate_max_balance_usd"] == 0
    assert result["requires_fbar"] is False


def test_missing_accounts_key_aggregates_to_zero():
    result = fbar_mod.process_fbar_check("o7", {"tax_year": 2024})
    assert result["aggregate_max_balance_usd"] == 0


def test_missing_tax_year_defaults_to_prior_year():
    result = fbar_mod.process_fbar_check("o8", {"accounts": [_account(5000)]})
    expected_year = date.today().year - 1
    assert result["filing_deadline"] == f"{expected_year + 1}-10-15"


def test_null_max_balance_treated_as_zero():
    result = fbar_mod.process_fbar_check("o9", {
        "tax_year": 2024,
        "accounts": [_account(5000), _account(None), _account(6000)],
    })
    assert result["aggregate_max_balance_usd"] == 11000


def test_empty_string_max_balance_treated_as_zero():
    result = fbar_mod.process_fbar_check("o10", {
        "tax_year": 2024,
        "accounts": [{"institution_name": "X", "max_balance_usd": ""}, _account(5000)],
    })
    assert result["aggregate_max_balance_usd"] == 5000


# --- deadline math ---

def test_deadline_is_oct_15_of_following_year():
    """Post-FinCEN-2017, FBAR deadline is April 15 auto-extended to Oct 15."""
    result = fbar_mod.process_fbar_check("o11", {"tax_year": 2024, "accounts": [_account(1)]})
    assert result["filing_deadline"] == "2025-10-15"


def test_deadline_for_old_year():
    result = fbar_mod.process_fbar_check("o12", {"tax_year": 2019, "accounts": [_account(1)]})
    assert result["filing_deadline"] == "2020-10-15"


# --- output shape ---

def test_result_includes_accounts_for_display():
    accounts = [_account(5000, institution_name="ICBC"), _account(6000, institution_name="Mizuho")]
    result = fbar_mod.process_fbar_check("o13", {"tax_year": 2024, "accounts": accounts})
    assert len(result["accounts"]) == 2


def test_result_includes_artifact_path(tmp_path):
    result = fbar_mod.process_fbar_check("artifact-test", {"tax_year": 2024, "accounts": [_account(5000)]})
    assert len(result["artifacts"]) == 1
    from pathlib import Path
    artifact_path = Path(result["artifacts"][0]["path"])
    assert artifact_path.exists()
    assert artifact_path.suffix == ".pdf"


def test_many_accounts_aggregate_correctly():
    accounts = [_account(100) for _ in range(50)]
    result = fbar_mod.process_fbar_check("o14", {"tax_year": 2024, "accounts": accounts})
    assert result["aggregate_max_balance_usd"] == 5000
    assert result["requires_fbar"] is False


def test_summary_formats_aggregate_with_two_decimals():
    result = fbar_mod.process_fbar_check("o15", {"tax_year": 2024, "accounts": [_account(7500.5)]})
    assert "$7,500.50" in result["summary"]


def test_next_steps_differ_between_required_and_not():
    required = fbar_mod.process_fbar_check("o16", {"tax_year": 2024, "accounts": [_account(15000)]})
    not_required = fbar_mod.process_fbar_check("o17", {"tax_year": 2024, "accounts": [_account(5000)]})
    assert any("BSA" in step or "FinCEN" in step for step in required["next_steps"])
    assert not any("BSA" in step or "FinCEN" in step for step in not_required["next_steps"])
