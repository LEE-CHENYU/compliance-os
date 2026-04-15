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


# --- entity match type (added in batch 2 of check-quality fixes) ---

def test_entity_exact_match():
    r = compare_fields("petitioner", "Acme Robotics Inc", "Acme Robotics Inc", "entity")
    assert r.status == "match"
    assert r.match_type == "entity"


def test_entity_whitespace_and_case_insensitive():
    r = compare_fields("petitioner", "  ACME ROBOTICS INC  ", "acme robotics inc", "entity")
    assert r.status == "match"


def test_entity_inc_vs_llc_is_mismatch():
    """Inc vs LLC is a legal entity-type difference that USCIS will flag."""
    r = compare_fields("petitioner", "Acme Robotics Inc", "Acme Robotics LLC", "entity")
    assert r.status == "mismatch"
    assert r.detail is not None
    assert "inc" in r.detail.lower() and "llc" in r.detail.lower()


def test_entity_corp_vs_incorporated_is_mismatch():
    r = compare_fields("petitioner", "Acme Robotics Corp", "Acme Robotics Incorporated", "entity")
    assert r.status == "mismatch"


def test_entity_inc_with_period_matches_inc():
    """'Acme Inc.' should match 'Acme Inc' — just punctuation differences."""
    r = compare_fields("petitioner", "Acme Inc.", "Acme Inc", "entity")
    assert r.status == "match"


def test_entity_llc_variant_forms_match():
    """'L.L.C.' and 'LLC' are the same legal entity suffix."""
    r = compare_fields("petitioner", "Foo L.L.C.", "Foo LLC", "entity")
    assert r.status == "match"


def test_entity_base_name_mismatch_is_mismatch():
    r = compare_fields("petitioner", "Acme Corp", "Widget Corp", "entity")
    assert r.status == "mismatch"


def test_entity_one_side_has_suffix_other_does_not():
    """'Acme Robotics' vs 'Acme Robotics Inc' — base matches, suffix on one side only."""
    r = compare_fields("petitioner", "Acme Robotics", "Acme Robotics Inc", "entity")
    assert r.status == "match"  # base matches, suffix asymmetry is noted in detail
    assert r.detail is not None and "suffix" in r.detail.lower()


def test_entity_missing_value():
    r = compare_fields("petitioner", "Acme Inc", None, "entity")
    assert r.status == "needs_review"


def test_entity_near_match_base_passes_threshold():
    """Typo/variation in base name, same suffix — should still match if base ≥92%."""
    r = compare_fields("petitioner", "Acme Robotics Inc", "Acme Robotic Inc", "entity")
    # 'robotics' vs 'robotic' = ~95% similarity → match
    assert r.status == "match"


def test_entity_far_apart_base_fails_threshold():
    """Same suffix but base names very different → mismatch."""
    r = compare_fields("petitioner", "Acme Inc", "Gigantic Industries Inc", "entity")
    assert r.status == "mismatch"


def test_entity_ltd_vs_limited_is_match():
    """'Ltd' and 'Limited' are the same suffix canonicalized."""
    r = compare_fields("petitioner", "Acme Ltd", "Acme Limited", "entity")
    assert r.status == "match"


def test_entity_gmbh_international_suffix():
    r_match = compare_fields("petitioner", "Acme GmbH", "Acme GMBH", "entity")
    assert r_match.status == "match"
    r_mismatch = compare_fields("petitioner", "Acme GmbH", "Acme AG", "entity")
    assert r_mismatch.status == "mismatch"


def test_unknown_match_type_returns_needs_review():
    r = compare_fields("x", "a", "b", "semantic")  # not implemented
    assert r.status == "needs_review"
    assert r.detail is not None and "Unknown match type" in r.detail
