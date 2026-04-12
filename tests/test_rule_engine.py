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


def test_nra_exemption_blocks_fbar_3520_fatca(engine):
    """NRAs (F-1/OPT/STEM OPT in first 5 years) should NOT get FBAR/3520/FATCA findings."""
    ctx = EvaluationContext(
        answers={
            "stage": "stem_opt",
            "years_in_us": 3,
            "has_foreign_accounts": "yes",
            "received_foreign_gifts": "yes",
        },
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    ids = [f.rule_id for f in engine.evaluate(ctx)]
    assert "foreign_accounts_fbar_risk" not in ids
    assert "foreign_gifts_3520_risk" not in ids
    assert "advisory_fbar" not in ids
    assert "advisory_fatca_8938" not in ids


def test_tax_resident_gets_fbar_3520_fatca(engine):
    """Tax residents (F-1 with 6+ years, H-1B) SHOULD get FBAR/3520/FATCA findings."""
    # F-1 with 7 years → tax resident
    ctx = EvaluationContext(
        answers={
            "stage": "stem_opt",
            "years_in_us": 7,
            "has_foreign_accounts": "yes",
            "received_foreign_gifts": "yes",
        },
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    ids = [f.rule_id for f in engine.evaluate(ctx)]
    assert "foreign_accounts_fbar_risk" in ids
    assert "foreign_gifts_3520_risk" in ids
    assert "advisory_fbar" in ids
    assert "advisory_fatca_8938" in ids


def test_h1b_is_tax_resident_for_fbar(engine):
    """H-1B holders are tax residents even with <5 years in the US."""
    ctx = EvaluationContext(
        answers={
            "stage": "h1b",
            "years_in_us": 2,
            "has_foreign_accounts": "yes",
            "received_foreign_gifts": "yes",
        },
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    ids = [f.rule_id for f in engine.evaluate(ctx)]
    assert "foreign_accounts_fbar_risk" in ids
    assert "foreign_gifts_3520_risk" in ids


def test_explicit_nra_status_overrides_years(engine):
    """Explicit tax_residency_status takes precedence over years heuristic."""
    ctx = EvaluationContext(
        answers={
            "stage": "stem_opt",
            "years_in_us": 10,
            "tax_residency_status": "Nonresident alien",
            "has_foreign_accounts": "yes",
            "received_foreign_gifts": "yes",
        },
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    ids = [f.rule_id for f in engine.evaluate(ctx)]
    assert "foreign_accounts_fbar_risk" not in ids
    assert "foreign_gifts_3520_risk" not in ids


def test_is_nra_does_not_mutate_original_answers():
    """EvaluationContext should not mutate the original answers dict."""
    original = {"stage": "opt", "years_in_us": 2}
    ctx = EvaluationContext(
        answers=original,
        extraction_a={},
        extraction_b={},
        comparisons={},
    )
    assert "is_nra" not in original
    assert ctx.answers["is_nra"] == "yes"


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


def test_derive_nra_accepts_lowercase_nonresident_variants():
    """_derive_nra should accept common case/format variants of nonresident alien."""
    from compliance_os.web.services.rule_engine import EvaluationContext
    for variant in ["nonresident", "Nonresident Alien", "NONRESIDENT ALIEN",
                    "non-resident alien", "  nra  ", "Nonresident alien"]:
        ctx = EvaluationContext(
            answers={"tax_residency_status": variant, "stage": "h1b"},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        assert ctx.answers["is_nra"] == "yes", f"variant {variant!r} should yield is_nra=yes"


def test_derive_nra_accepts_resident_variants():
    from compliance_os.web.services.rule_engine import EvaluationContext
    for variant in ["Resident alien", "resident", "RESIDENT ALIEN"]:
        ctx = EvaluationContext(
            answers={"tax_residency_status": variant, "stage": "stem_opt", "years_in_us": 2},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        assert ctx.answers["is_nra"] == "no", f"variant {variant!r} should yield is_nra=no"


def test_derive_nra_unknown_value_falls_through_to_heuristics():
    """Unknown tax_residency_status should not default to 'no' — it should
    fall through to stage-based heuristics (branch 2+)."""
    from compliance_os.web.services.rule_engine import EvaluationContext
    # Unknown string + stem_opt stage + years < 6 → should use branch 2, yielding yes
    ctx = EvaluationContext(
        answers={"tax_residency_status": "somewhere-in-between", "stage": "stem_opt", "years_in_us": 2},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    assert ctx.answers["is_nra"] == "yes", \
        "unknown tax_residency_status should fall through to branch 2, not default to 'no'"


def test_duties_low_relevance_fires_on_low_confidence():
    """The duties_low_relevance rule should fire when a comparison dict has
    confidence below the threshold. Regression test for the engine bug where
    lt/gt couldn't compare numeric thresholds against dict-shaped comparisons."""
    from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine
    engine = RuleEngine.from_yaml("config/rules/stem_opt.yaml")
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={}, extraction_b={},
        comparisons={"duties": {"status": "mismatch", "confidence": 0.42}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "duties_low_relevance" in rule_ids, \
        f"duties_low_relevance should fire with confidence=0.42 < 0.6; got fired={rule_ids}"


def test_duties_low_relevance_does_not_fire_on_high_confidence():
    """Companion test: duties_low_relevance should NOT fire when confidence >= 0.6."""
    from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine
    engine = RuleEngine.from_yaml("config/rules/stem_opt.yaml")
    ctx = EvaluationContext(
        answers={"stage": "stem_opt", "years_in_us": 3},
        extraction_a={}, extraction_b={},
        comparisons={"duties": {"status": "match", "confidence": 0.85}},
    )
    findings = engine.evaluate(ctx)
    rule_ids = [f.rule_id for f in findings]
    assert "duties_low_relevance" not in rule_ids, \
        f"duties_low_relevance should NOT fire with confidence=0.85 > 0.6; got fired={rule_ids}"


def test_derive_nra_accepts_owner_residency_nonresident_variants():
    """_derive_nra branch 4 should accept common non-resident-alien variants
    of owner_residency, not just the literal 'outside_us'."""
    from compliance_os.web.services.rule_engine import EvaluationContext
    for variant in [
        "outside_us",
        "nonresident",
        "non_resident",
        "non-resident",
        "nonresident_alien",
        "non-resident alien",
        "NONRESIDENT_ALIEN",
        "  nra  ",
        "NRA",
    ]:
        ctx = EvaluationContext(
            answers={"owner_residency": variant},
            extraction_a={}, extraction_b={}, comparisons={},
        )
        assert ctx.answers["is_nra"] == "yes", (
            f"owner_residency={variant!r} should yield is_nra=yes"
        )


def test_derive_nra_us_citizen_or_pr_still_returns_no():
    """Regression: us_citizen_or_pr must still yield is_nra=no (default)."""
    from compliance_os.web.services.rule_engine import EvaluationContext
    ctx = EvaluationContext(
        answers={"owner_residency": "us_citizen_or_pr"},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    assert ctx.answers["is_nra"] == "no"


def test_derive_nra_unknown_owner_residency_falls_through_to_default():
    """Unknown owner_residency values should fall through to default 'no',
    not accidentally get mapped to 'yes'."""
    from compliance_os.web.services.rule_engine import EvaluationContext
    ctx = EvaluationContext(
        answers={"owner_residency": "somewhere-unclassified"},
        extraction_a={}, extraction_b={}, comparisons={},
    )
    assert ctx.answers["is_nra"] == "no"
