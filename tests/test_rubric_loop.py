"""Tests for scripts/rubric/ package — codex-backed rubric evaluation harness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable so `from rubric import ...` works in tests
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import pytest

from rubric.models import (
    CaseSpec,
    FixtureRecord,
    EvalRecord,
    JudgeRecord,
    Scorecard,
    CallTelemetry,
    CodexCallResult,
    CodexCallError,
    CoverageGap,
)
from rubric.case_ids import build_case_id, parse_case_id, validate_case_id
from rubric.hints import build_field_reference_table, gather_rule_fields
from rubric.io import (
    PROJECT_ROOT,
    FIXTURE_DIR,
    GOLDENS_DIR,
    EVAL_CACHE_DIR,
    JUDGE_CACHE_DIR,
    sha256_of_obj,
    sha256_of_text,
    save_json,
    load_json,
    ensure_dirs,
)


def test_case_spec_roundtrip_to_dict():
    spec = CaseSpec(
        case_id="A-stem_opt-job_title_mismatch-pos",
        slice="A",
        track="stem_opt",
        target_rule_id="job_title_mismatch",
        probe_intent="engine must fire job_title_mismatch",
        gen_strategy="llm",
    )
    d = spec.to_dict()
    assert d["case_id"] == "A-stem_opt-job_title_mismatch-pos"
    assert d["slice"] == "A"
    # Roundtrip through JSON — this is what hitting disk looks like.
    # Catches field types that can't survive JSON serialization.
    restored = CaseSpec.from_dict(json.loads(json.dumps(d)))
    assert restored == spec


def test_call_telemetry_accumulates():
    t = CallTelemetry()
    t.generator_calls += 1
    t.tokens_in_total += 500
    assert t.generator_calls == 1
    assert t.tokens_in_total == 500


def test_coverage_gap_is_exception_subclass():
    assert issubclass(CoverageGap, Exception)
    with pytest.raises(CoverageGap, match="job_title"):
        raise CoverageGap("missing rules: ['job_title_mismatch']")


def test_codex_call_error_carries_kind():
    err = CodexCallError(kind="timeout", message="took too long")
    assert err.kind == "timeout"
    assert "took too long" in str(err)


def test_codex_call_error_pickles():
    import pickle
    err = CodexCallError(kind="timeout", message="took too long", stderr="boom", attempts=3)
    loaded = pickle.loads(pickle.dumps(err))
    assert loaded.kind == "timeout"
    assert loaded.message == "took too long"
    assert loaded.stderr == "boom"
    assert loaded.attempts == 3
    assert str(loaded) == "took too long"


def test_build_case_id_format():
    cid = build_case_id(slice="A", track="stem_opt", rule_id="job_title_mismatch", polarity="pos")
    assert cid == "A-stem_opt-job_title_mismatch-pos"


def test_parse_case_id_roundtrip():
    cid = "B-entity-missing_5472-neg"
    parsed = parse_case_id(cid)
    assert parsed == {
        "slice": "B",
        "track": "entity",
        "rule_id": "missing_5472",
        "polarity": "neg",
    }


def test_parse_case_id_handles_rule_ids_with_underscores():
    # Rule IDs frequently contain underscores — parse must not split on them
    cid = "A-stem_opt-employer_change_stem_i983-pos"
    parsed = parse_case_id(cid)
    assert parsed["rule_id"] == "employer_change_stem_i983"


def test_validate_case_id_accepts_goldens():
    # Goldens have free-form IDs like "C-operator-contains-scalar"
    validate_case_id("C-operator-contains-scalar")
    validate_case_id("E-edge-false-string-gotcha")


def test_validate_case_id_rejects_bad_slice():
    with pytest.raises(ValueError, match="slice"):
        validate_case_id("Z-stem_opt-job_title_mismatch-pos")


def test_validate_case_id_rejects_empty():
    with pytest.raises(ValueError):
        validate_case_id("")


def test_build_case_id_rejects_empty_track():
    with pytest.raises(ValueError, match="track"):
        build_case_id(slice="A", track="", rule_id="some_rule", polarity="pos")


def test_build_case_id_rejects_empty_rule_id():
    with pytest.raises(ValueError, match="rule_id"):
        build_case_id(slice="A", track="stem_opt", rule_id="", polarity="pos")


def test_build_case_id_rejects_hyphen_in_track():
    with pytest.raises(ValueError, match="'-'"):
        build_case_id(slice="A", track="stem-opt", rule_id="some_rule", polarity="pos")


def test_build_case_id_rejects_hyphen_in_rule_id():
    with pytest.raises(ValueError, match="'-'"):
        build_case_id(slice="A", track="stem_opt", rule_id="some-rule", polarity="pos")


def test_gather_rule_fields_from_sample_yaml(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "fake.yaml").write_text("""
version: "0.1.0"
rules:
  - id: sample_rule
    track: fake
    type: logic
    conditions:
      - field: stage
        operator: eq
        value: opt
        source: answers
      - field: employer_name
        operator: mismatch
        source: comparison
    severity: warning
    finding:
      title: fake
      action: fake
      consequence: fake
""")
    fields = gather_rule_fields(rules_dir)
    assert "stage" in fields
    assert "employer_name" in fields
    assert len(fields) == 2


def test_build_field_reference_table_includes_known_fields(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "stem_opt.yaml").write_text("""
version: "0.1.0"
rules:
  - id: r1
    track: stem_opt
    type: logic
    conditions:
      - field: stage
        operator: eq
        value: stem_opt
        source: answers
    severity: info
    finding: {title: x, action: x, consequence: x}
""")
    table = build_field_reference_table(rules_dir)
    assert "stage" in table
    assert "tax_residency_status" in table  # derivation input always included
    assert "is_nra" in table                  # always documented as derived


def test_sha256_of_obj_is_stable():
    obj = {"b": 2, "a": 1}
    assert sha256_of_obj(obj) == sha256_of_obj({"a": 1, "b": 2})  # key order independent


def test_sha256_of_text_matches_expected():
    assert sha256_of_text("hello") == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_save_and_load_json_roundtrip(tmp_path):
    path = tmp_path / "sub" / "file.json"
    payload = {"hello": "world", "n": 42}
    save_json(path, payload)
    assert path.exists()
    assert load_json(path) == payload


def test_ensure_dirs_creates_missing_paths(tmp_path):
    p = tmp_path / "a" / "b" / "c"
    ensure_dirs(p)
    assert p.is_dir()
    ensure_dirs(p)  # idempotent
