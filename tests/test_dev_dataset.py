"""Integration test: run dev_dataset through the extraction + rule pipeline.

This tests that our general-purpose rules correctly identify real compliance
issues from real documents. The dev_dataset represents one user's situation,
but the rules should work for any user with similar characteristics.
"""
import pytest
from pathlib import Path

from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

DEV = Path(__file__).parent.parent / "dev_dataset"


@pytest.fixture
def stem_opt_engine():
    return RuleEngine.from_yaml("config/rules/stem_opt.yaml")


@pytest.fixture
def entity_engine():
    return RuleEngine.from_yaml("config/rules/entity.yaml")


# ============================================================
# Young Professional track — based on dev_dataset person
# F-1 student, CPT at CIAM, previously on STEM OPT,
# changed employers multiple times, has investment income
# ============================================================

class TestYoungProfessionalRules:
    """Test that answer-based rules fire for a typical F-1 professional."""

    def test_unemployment_flagged_when_between_jobs(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "opt", "years_in_us": 3, "employment_status": "between_jobs", "employer_changed": "yes"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "unemployment_risk" in ids
        assert "employer_change_unreported" in ids

    def test_stem_opt_employer_change_requires_new_i983(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "stem_opt", "years_in_us": 4, "employment_status": "employed", "employer_changed": "yes"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "employer_change_stem_i983" in ids

    def test_h1b_unemployment_is_critical(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "h1b", "years_in_us": 5, "employment_status": "not_employed", "employer_changed": "no", "petition_status": "approved"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        findings = stem_opt_engine.evaluate(ctx)
        h1b_unemp = next(f for f in findings if f.rule_id == "h1b_unemployment")
        assert h1b_unemp.severity == "critical"

    def test_h1b_pending_travel_warning(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "h1b", "years_in_us": 5, "employment_status": "employed", "employer_changed": "no", "petition_status": "pending"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "h1b_pending_no_travel" in ids

    def test_fbar_not_shown_under_5_years(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "stem_opt", "years_in_us": 3, "employment_status": "employed"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "advisory_fbar" not in ids

    def test_fbar_shown_over_5_years(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "h1b", "years_in_us": 7, "employment_status": "employed", "employer_changed": "no", "petition_status": "approved"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "advisory_fbar" in ids
        assert "advisory_fatca_8938" in ids

    def test_document_mismatch_fires_location_and_ar11(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "stem_opt", "years_in_us": 3, "employment_status": "employed"},
            extraction_a={}, extraction_b={},
            comparisons={
                "job_title": {"status": "match", "confidence": 0.95},
                "work_location": {"status": "mismatch", "confidence": 0.2},
                "compensation": {"status": "match", "confidence": 1.0},
            },
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "location_mismatch" in ids
        assert "advisory_ar11" in ids
        assert "advisory_multistate_tax" in ids

    def test_i140_portability_warning(self, stem_opt_engine):
        ctx = EvaluationContext(
            answers={"stage": "i140", "years_in_us": 8, "employment_status": "employed", "employer_changed": "yes", "petition_status": "pending"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in stem_opt_engine.evaluate(ctx)]
        assert "i140_employer_change_portability" in ids
        assert "i140_pending_limited_options" in ids


# ============================================================
# Entrepreneur track — based on dev_dataset LLC
# Foreign-owned SMLLC (Wyoming), NRA owner on F-1,
# formed 2023 (3+ years ago), foreign capital transfers
# ============================================================

class TestEntrepreneurRules:
    """Test that entity rules fire for a typical foreign-owned LLC."""

    def test_nra_smllc_missing_5472(self, entity_engine):
        """Foreign-owned SMLLC without 5472 = $25K/year penalty."""
        ctx = EvaluationContext(
            answers={
                "entity_type": "smllc",
                "owner_residency": "on_visa",
                "state_of_formation": "Wyoming",
                "separate_bank_account": "yes",
                "foreign_capital_transfer": "yes",
                "formation_age": "3_plus_years",
                "visa_type": "f1_opt_stem",
            },
            extraction_a={},
            extraction_b={"form_5472_present": "False", "form_type": "1040"},
            comparisons={},
        )
        findings = entity_engine.evaluate(ctx)
        ids = [f.rule_id for f in findings]

        # Should fire: missing 5472, wrong form type, schedule C on OPT,
        # foreign capital, cumulative penalty, zero-revenue filing
        assert "missing_5472" in ids
        assert "wrong_form_type" in ids
        assert "foreign_capital_undocumented" in ids
        assert "cumulative_5472_penalty" in ids
        assert "no_revenue_still_must_file" in ids

    def test_nra_scorp_invalid(self, entity_engine):
        """NRA + S-Corp election = void retroactively."""
        ctx = EvaluationContext(
            answers={"entity_type": "smllc", "owner_residency": "on_visa", "formation_age": "1_2_years"},
            extraction_a={},
            extraction_b={"form_type": "1120-S"},
            comparisons={},
        )
        findings = entity_engine.evaluate(ctx)
        critical = [f for f in findings if f.severity == "critical"]
        assert any(f.rule_id == "nra_scorp_invalid" for f in critical)

    def test_corporate_veil_no_bank_account(self, entity_engine):
        ctx = EvaluationContext(
            answers={"entity_type": "smllc", "owner_residency": "us_citizen_or_pr", "separate_bank_account": "no", "formation_age": "1_2_years"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in entity_engine.evaluate(ctx)]
        assert "corporate_veil_risk" in ids

    def test_first_year_deadlines(self, entity_engine):
        ctx = EvaluationContext(
            answers={"entity_type": "c_corp", "owner_residency": "us_citizen_or_pr", "formation_age": "this_year", "separate_bank_account": "yes", "foreign_capital_transfer": "no"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in entity_engine.evaluate(ctx)]
        assert "first_year_filing_deadlines" in ids

    def test_advisory_gating_us_citizen(self, entity_engine):
        """US citizen should NOT see BOI advisory, SHOULD see annual report."""
        ctx = EvaluationContext(
            answers={"entity_type": "smllc", "owner_residency": "us_citizen_or_pr", "formation_age": "1_2_years", "separate_bank_account": "yes", "foreign_capital_transfer": "no"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in entity_engine.evaluate(ctx)]
        assert "advisory_boi_foreign" not in ids
        assert "advisory_state_annual_report" in ids
        assert "advisory_registered_agent" in ids

    def test_dividend_withholding_ccorp_nra(self, entity_engine):
        ctx = EvaluationContext(
            answers={"entity_type": "c_corp", "owner_residency": "outside_us", "formation_age": "1_2_years", "separate_bank_account": "yes", "foreign_capital_transfer": "no"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        ids = [f.rule_id for f in entity_engine.evaluate(ctx)]
        assert "advisory_dividend_withholding" in ids
        assert "advisory_boi_foreign" in ids


# ============================================================
# Cross-domain: the dev_dataset person is BOTH a young
# professional AND an entrepreneur. Test that both rule sets
# fire correctly for the same individual's characteristics.
# ============================================================

class TestCrossDomainRisks:
    """The real power of Guardian: cross-domain risk detection."""

    def test_f1_student_with_llc_schedule_c(self, entity_engine):
        """F-1 student running an LLC + Schedule C = unauthorized work risk."""
        ctx = EvaluationContext(
            answers={
                "entity_type": "smllc",
                "owner_residency": "on_visa",
                "visa_type": "f1_opt_stem",
                "formation_age": "3_plus_years",
                "separate_bank_account": "yes",
                "foreign_capital_transfer": "yes",
            },
            extraction_a={},
            extraction_b={"schedules_present": ["schedule_c"], "form_type": "1040", "form_5472_present": "False"},
            comparisons={},
        )
        findings = entity_engine.evaluate(ctx)
        ids = [f.rule_id for f in findings]

        # Immigration risk from entity track
        assert "schedule_c_on_opt" in ids
        # Tax risk
        assert "wrong_form_type" in ids
        # Entity risk
        assert "missing_5472" in ids
        assert "cumulative_5472_penalty" in ids
        # Foreign capital
        assert "foreign_capital_undocumented" in ids

    def test_severity_ordering(self, entity_engine):
        """Critical findings should come before warnings before info."""
        ctx = EvaluationContext(
            answers={
                "entity_type": "smllc",
                "owner_residency": "on_visa",
                "visa_type": "f1_opt_stem",
                "formation_age": "3_plus_years",
                "separate_bank_account": "no",
                "foreign_capital_transfer": "yes",
            },
            extraction_a={},
            extraction_b={"form_type": "1120-S", "form_5472_present": "False", "schedules_present": ["schedule_c"]},
            comparisons={},
        )
        findings = entity_engine.evaluate(ctx)
        severities = [f.severity for f in findings]
        order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(len(severities) - 1):
            assert order[severities[i]] <= order[severities[i + 1]], \
                f"Severity out of order: {severities[i]} before {severities[i+1]}"
