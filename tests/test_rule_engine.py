"""Tests for the YAML-based compliance rule engine."""
import pytest
from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine


@pytest.fixture
def engine():
    return RuleEngine.from_yaml("config/rules/stem_opt.yaml")


def test_load_rules(engine):
    assert len(engine.rules) > 0
    rule_ids = [r.id for r in engine.rules]
    assert "job_title_mismatch" in rule_ids
    assert "advisory_fbar" in rule_ids


def test_comparison_rule_fires_on_mismatch(engine):
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={"job_title": {"status": "mismatch", "confidence": 0.3}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "job_title_mismatch" in rule_ids


def test_comparison_rule_does_not_fire_on_match(engine):
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={"job_title": {"status": "match", "confidence": 0.95}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "job_title_mismatch" not in rule_ids


def test_advisory_gated_on_years(engine):
    ctx_short = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    ctx_long = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 7},
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    short_ids = [f.rule_id for f in engine.evaluate(ctx_short)]
    long_ids = [f.rule_id for f in engine.evaluate(ctx_long)]
    assert "advisory_fbar" not in short_ids
    assert "advisory_fbar" in long_ids


def test_logic_rule_grace_period(engine):
    ctx = EvaluationContext(
        answers={"stage": "opt", "years_in_us": 2},
        extraction_a={"end_date": "2025-12-01"},
        extraction_b={},
        comparisons={},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "grace_period_employment" in rule_ids


def test_findings_sorted_by_severity(engine):
    ctx = EvaluationContext(
        answers={"stage": "opt", "years_in_us": 7},
        extraction_a={"end_date": "2025-12-01"},
        extraction_b={},
        comparisons={"job_title": {"status": "mismatch", "confidence": 0.3}},
    )
    findings = engine.evaluate(ctx)
    severities = [f.severity for f in findings]
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    for i in range(len(severities) - 1):
        assert severity_order[severities[i]] <= severity_order[severities[i + 1]]


def test_entity_rules_load():
    e = RuleEngine.from_yaml("config/rules/entity.yaml")
    assert len(e.rules) == 15
    ids = [r.id for r in e.rules]
    assert "nra_scorp_invalid" in ids
    assert "advisory_boi_foreign" in ids


def test_entity_nra_scorp():
    e = RuleEngine.from_yaml("config/rules/entity.yaml")
    ctx = EvaluationContext(
        answers={"owner_residency": "on_visa", "entity_type": "smllc"},
        extraction_a={},
        extraction_b={"form_type": "1120-S"},
        comparisons={},
    )
    findings = e.evaluate(ctx)
    ids = [f.rule_id for f in findings]
    assert "nra_scorp_invalid" in ids


def test_entity_corporate_veil():
    e = RuleEngine.from_yaml("config/rules/entity.yaml")
    ctx = EvaluationContext(
        answers={"owner_residency": "us_citizen_or_pr", "entity_type": "smllc", "separate_bank_account": "no"},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    findings = e.evaluate(ctx)
    ids = [f.rule_id for f in findings]
    assert "corporate_veil_risk" in ids


def test_entity_advisory_gating():
    e = RuleEngine.from_yaml("config/rules/entity.yaml")
    # US citizen should not see BOI advisory
    ctx = EvaluationContext(
        answers={"owner_residency": "us_citizen_or_pr", "entity_type": "c_corp"},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    ids = [f.rule_id for f in e.evaluate(ctx)]
    assert "advisory_boi_foreign" not in ids
    # Outside US should see BOI
    ctx2 = EvaluationContext(
        answers={"owner_residency": "outside_us", "entity_type": "c_corp"},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    ids2 = [f.rule_id for f in e.evaluate(ctx2)]
    assert "advisory_boi_foreign" in ids2


def test_needs_review_triggers_mismatch_rule(engine):
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={},
        extraction_b={},
        comparisons={"work_location": {"status": "needs_review", "confidence": 0.0}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "location_mismatch" in rule_ids


def test_data_room_rules_load_and_fire():
    engine = RuleEngine.from_yaml("config/rules/data_room.yaml")

    ctx = EvaluationContext(
        answers={"stage": "data_room"},
        extraction_a={},
        extraction_b={},
        comparisons={"passport_ead_date_of_birth": {"status": "mismatch", "confidence": 0.0}},
    )

    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]

    assert "passport_ead_birthdate_mismatch" in rule_ids
