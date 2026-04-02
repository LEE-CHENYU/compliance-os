"""Tests for the field comparison engine."""
import pytest
from compliance_os.web.services.comparator import compare_fields


def test_exact_match():
    r = compare_fields("employer_name", "Acme Corp", "Acme Corp", "exact")
    assert r.status == "match"


def test_exact_match_case_insensitive():
    r = compare_fields("employer_name", "Acme Corp", "acme corp", "exact")
    assert r.status == "match"


def test_exact_mismatch():
    r = compare_fields("employer_name", "Acme Corp", "Beta LLC", "exact")
    assert r.status == "mismatch"


def test_fuzzy_match():
    r = compare_fields("job_title", "Senior Data Analyst", "Sr. Data Analyst", "fuzzy")
    assert r.status == "match"


def test_fuzzy_mismatch():
    r = compare_fields("job_title", "Data Analyst", "Marketing Manager", "fuzzy")
    assert r.status == "mismatch"


def test_numeric_match():
    r = compare_fields("compensation", "85000", "85000", "numeric")
    assert r.status == "match"


def test_numeric_within_tolerance():
    r = compare_fields("compensation", "85000", "85200", "numeric")
    assert r.status == "match"


def test_numeric_mismatch():
    r = compare_fields("compensation", "85000", "52000", "numeric")
    assert r.status == "mismatch"


def test_missing_value():
    r = compare_fields("job_title", "Data Analyst", None, "fuzzy")
    assert r.status == "needs_review"


def test_both_missing():
    r = compare_fields("job_title", None, None, "fuzzy")
    assert r.status == "needs_review"


def test_numeric_with_dollar_signs():
    r = compare_fields("compensation", "$85,000", "$85,000", "numeric")
    assert r.status == "match"
