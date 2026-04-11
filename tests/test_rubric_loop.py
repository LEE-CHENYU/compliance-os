"""Tests for scripts/rubric/ package — codex-backed rubric evaluation harness."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

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
from rubric.evaluate import evaluate_case, load_eval_cache
from rubric.models import FixtureRecord
from rubric.codex_client import call_codex, CodexCallError as CcError
from rubric.codex_client import _extract_token_counts
from rubric.judge import (
    judge_case,
    compute_judge_cache_key,
    filter_criteria_for_slice,
    render_judge_prompt,
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


from rubric.discover import (
    build_manifest,
    build_positive_intent,
    build_negative_intent,
)
from rubric.models import CoverageGap


def _write_sample_rules(rules_dir: Path) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "stem_opt.yaml").write_text("""
version: "0.1.0"
rules:
  - id: sample_rule_a
    track: stem_opt
    type: logic
    conditions:
      - field: stage
        operator: eq
        value: stem_opt
        source: answers
    severity: warning
    finding: {title: T, action: A, consequence: C}
""")


def test_discover_creates_ab_pair_per_rule(tmp_path):
    rules_dir = tmp_path / "rules"
    goldens_dir = tmp_path / "goldens"
    goldens_dir.mkdir(parents=True)
    _write_sample_rules(rules_dir)

    cases = build_manifest(rules_dir, goldens_dir)
    case_ids = {c.case_id for c in cases}
    assert "A-stem_opt-sample_rule_a-pos" in case_ids
    assert "B-stem_opt-sample_rule_a-neg" in case_ids
    assert len(cases) == 2


def test_discover_loads_static_goldens(tmp_path):
    rules_dir = tmp_path / "rules"
    goldens_dir = tmp_path / "goldens"
    _write_sample_rules(rules_dir)
    goldens_dir.mkdir(parents=True)
    (goldens_dir / "C-operator-test.json").write_text(json.dumps({
        "case_id": "C-operator-test",
        "slice": "C",
        "track": "stem_opt",
        "target_rule_id": None,
        "probe_intent": "probe the contains operator on a scalar",
        "generated_by": "hand",
        "generated_at": "2026-04-10T00:00:00Z",
        "generator_prompt_hash": None,
        "flavor_hint": None,
        "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        "expected": {
            "must_fire_rule_ids": [],
            "must_not_fire_rule_ids": [],
            "expected_nra": "no",
            "expected_track": "stem_opt",
            "notes": "contains on scalar returns False",
        },
    }))
    cases = build_manifest(rules_dir, goldens_dir)
    golden_cases = [c for c in cases if c.slice == "C"]
    assert len(golden_cases) == 1
    assert golden_cases[0].case_id == "C-operator-test"
    assert golden_cases[0].gen_strategy == "golden"
    assert golden_cases[0].fixture_content is not None


def test_discover_auto_expands_manifest_when_rules_added(tmp_path):
    """If a rule YAML has a rule that has NO entry in the discover function's
    output (impossible today but a guard for future refactors), CoverageGap fires."""
    rules_dir = tmp_path / "rules"
    goldens_dir = tmp_path / "goldens"
    goldens_dir.mkdir(parents=True)

    _write_sample_rules(rules_dir)
    (goldens_dir / "C-covers-nothing.json").write_text(json.dumps({
        "case_id": "C-covers-nothing",
        "slice": "C",
        "track": "stem_opt",
        "target_rule_id": "sample_rule_a",
        "probe_intent": "covers",
        "generated_by": "hand",
        "generated_at": "2026-04-10T00:00:00Z",
        "generator_prompt_hash": None,
        "flavor_hint": None,
        "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        "expected": {"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                     "expected_nra": "no", "expected_track": "stem_opt", "notes": ""},
    }))
    cases = build_manifest(rules_dir, goldens_dir)
    assert len(cases) == 3  # A + B + C

    (rules_dir / "stem_opt.yaml").write_text("""
version: "0.1.0"
rules:
  - id: sample_rule_a
    track: stem_opt
    type: logic
    conditions: []
    severity: info
    finding: {title: T, action: A, consequence: C}
  - id: sample_rule_b
    track: stem_opt
    type: logic
    conditions: []
    severity: info
    finding: {title: T, action: A, consequence: C}
""")
    cases = build_manifest(rules_dir, goldens_dir)
    rule_ids_in_manifest = {c.target_rule_id for c in cases if c.target_rule_id}
    assert "sample_rule_a" in rule_ids_in_manifest
    assert "sample_rule_b" in rule_ids_in_manifest


def test_enforce_coverage_raises_when_rule_unseen(tmp_path):
    """_enforce_coverage must raise CoverageGap when rules_dir contains a rule
    that has no covering case in the passed-in cases list."""
    from rubric.discover import _enforce_coverage
    rules_dir = tmp_path / "rules"
    _write_sample_rules(rules_dir)  # writes sample_rule_a to stem_opt.yaml
    # Pass an empty cases list — sample_rule_a is in rules_dir but nothing covers it
    with pytest.raises(CoverageGap, match="sample_rule_a"):
        _enforce_coverage(rules_dir, cases=[])


def test_positive_intent_mentions_rule_id():
    rule = {
        "id": "job_title_mismatch",
        "conditions": [
            {"field": "job_title", "operator": "mismatch", "source": "comparison"},
        ],
    }
    intent = build_positive_intent(rule)
    assert "job_title_mismatch" in intent
    assert "mismatch" in intent or "fire" in intent


def test_negative_intent_describes_near_miss():
    rule = {
        "id": "job_title_mismatch",
        "conditions": [
            {"field": "job_title", "operator": "mismatch", "source": "comparison"},
        ],
    }
    intent = build_negative_intent(rule)
    assert "NOT" in intent or "not fire" in intent.lower()
    assert "job_title_mismatch" in intent


def test_positive_intent_preserves_condition_order():
    """Multi-condition rules must serialize in the order they appear in the YAML."""
    rule = {
        "id": "multi_cond_rule",
        "conditions": [
            {"source": "answers", "field": "a", "operator": "eq", "value": 1},
            {"source": "comparison", "field": "b", "operator": "mismatch"},
            {"source": "answers", "field": "c", "operator": "in", "value": [1, 2, 3]},
        ],
    }
    intent = build_positive_intent(rule)
    a_pos = intent.index("answers.a")
    b_pos = intent.index("comparison.b")
    c_pos = intent.index("answers.c")
    assert a_pos < b_pos < c_pos


def test_discover_loads_real_goldens_from_repo():
    """Smoke-test that the real goldens dir loads cleanly."""
    from rubric.io import GOLDENS_DIR, CONFIG_RULES_DIR
    if not GOLDENS_DIR.exists() or not any(GOLDENS_DIR.glob("*.json")):
        pytest.skip("no goldens yet")
    cases = build_manifest(CONFIG_RULES_DIR, GOLDENS_DIR)
    golden_cases = [c for c in cases if c.gen_strategy == "golden"]
    assert len(golden_cases) >= 6, f"expected ≥6 seed goldens, got {len(golden_cases)}"
    golden_ids = {c.case_id for c in golden_cases}
    assert "C-operator-contains-scalar" in golden_ids
    assert "E-edge-false-string-gotcha" in golden_ids


def _make_fixture(case_id: str, track: str, input_: dict, expected: dict) -> FixtureRecord:
    return FixtureRecord(
        case_id=case_id,
        slice=case_id[0],
        track=track,
        target_rule_id=None,
        probe_intent="test",
        generated_by="hand",
        generated_at="2026-04-10T00:00:00Z",
        generator_prompt_hash=None,
        flavor_hint=None,
        input=input_,
        expected=expected,
    )


def test_evaluate_case_fires_job_title_mismatch(tmp_path):
    """Feed a fixture that should fire job_title_mismatch, verify the engine agrees."""
    fixture = _make_fixture(
        case_id="A-stem_opt-job_title_mismatch-pos",
        track="stem_opt",
        input_={
            "answers": {"stage": "stem_opt", "years_in_us": 3},
            "extraction_a": {},
            "extraction_b": {},
            "comparisons": {"job_title": {"status": "mismatch", "confidence": 0.3}},
        },
        expected={
            "must_fire_rule_ids": ["job_title_mismatch"],
            "must_not_fire_rule_ids": [],
            "expected_nra": "yes",
            "expected_track": "stem_opt",
            "notes": "",
        },
    )
    cache_dir = tmp_path / "eval_cache"
    record = evaluate_case(fixture, cache_dir=cache_dir)
    rule_ids = [f["rule_id"] for f in record.findings]
    assert "job_title_mismatch" in rule_ids
    assert record.derived["is_nra"] == "yes"
    assert record.engine_error is None
    # Cache was written
    assert (cache_dir / "A-stem_opt-job_title_mismatch-pos.json").exists()


def test_evaluate_case_captures_derived_is_nra(tmp_path):
    fixture = _make_fixture(
        case_id="D-nra-branch1-explicit",
        track="stem_opt",
        input_={
            "answers": {"stage": "stem_opt", "years_in_us": 3, "tax_residency_status": "Resident alien"},
            "extraction_a": {},
            "extraction_b": {},
            "comparisons": {},
        },
        expected={
            "must_fire_rule_ids": [],
            "must_not_fire_rule_ids": [],
            "expected_nra": "no",
            "expected_track": "stem_opt",
            "notes": "",
        },
    )
    record = evaluate_case(fixture, cache_dir=tmp_path / "eval_cache")
    assert record.derived["is_nra"] == "no"  # branch-1 override


def test_evaluate_case_handles_unknown_track(tmp_path):
    """If the track has no rule file, engine_error is set and we don't crash."""
    fixture = _make_fixture(
        case_id="A-nonexistent_track-fake-pos",
        track="nonexistent_track",
        input_={"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        expected={"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                  "expected_nra": "no", "expected_track": "nonexistent_track", "notes": ""},
    )
    record = evaluate_case(fixture, cache_dir=tmp_path / "eval_cache")
    assert record.engine_error is not None
    assert "nonexistent_track" in record.engine_error


def test_load_eval_cache_returns_none_for_missing(tmp_path):
    assert load_eval_cache("nonexistent", tmp_path) is None


class _FakeProc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _make_schema(tmp_path: Path) -> Path:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["verdict"],
        "properties": {"verdict": {"type": "string"}},
    }))
    return schema_path


def test_call_codex_success_path(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)
    expected_output = {"verdict": "pass"}

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        # Simulate codex writing to --output-last-message
        out_file = cmd[cmd.index("--output-last-message") + 1]
        Path(out_file).write_text(json.dumps(expected_output))
        return _FakeProc(stdout='{"type":"usage","input_tokens":10,"output_tokens":5}\n')

    monkeypatch.setattr("subprocess.run", fake_run)
    result = call_codex(prompt="hi", schema_path=schema_path)
    assert result.parsed == {"verdict": "pass"}
    assert result.tokens_in == 10
    assert result.tokens_out == 5


def test_call_codex_retries_on_parse_failure(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)
    call_count = {"n": 0}

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        out_file = cmd[cmd.index("--output-last-message") + 1]
        call_count["n"] += 1
        if call_count["n"] == 1:
            Path(out_file).write_text("not valid json at all")
        else:
            Path(out_file).write_text(json.dumps({"verdict": "pass"}))
        return _FakeProc(stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = call_codex(prompt="hi", schema_path=schema_path)
    assert result.parsed == {"verdict": "pass"}
    assert result.attempts == 2


def test_call_codex_retries_on_schema_violation(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)
    call_count = {"n": 0}

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        out_file = cmd[cmd.index("--output-last-message") + 1]
        call_count["n"] += 1
        if call_count["n"] == 1:
            Path(out_file).write_text(json.dumps({"wrong_key": "oops"}))
        else:
            Path(out_file).write_text(json.dumps({"verdict": "pass"}))
        return _FakeProc(stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = call_codex(prompt="hi", schema_path=schema_path)
    assert result.parsed == {"verdict": "pass"}
    assert result.attempts == 2


def test_call_codex_raises_after_exhausting_retries(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        out_file = cmd[cmd.index("--output-last-message") + 1]
        Path(out_file).write_text("not json")
        return _FakeProc(stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(CcError) as exc_info:
        call_codex(prompt="hi", schema_path=schema_path, max_retries=1)
    assert exc_info.value.kind == "parse_failure"


def test_call_codex_falls_back_on_unsupported_model(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)
    calls = []
    timeouts = []

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        model_idx = cmd.index("--model") + 1
        model = cmd[model_idx]
        calls.append(model)
        timeouts.append(timeout)
        out_file = cmd[cmd.index("--output-last-message") + 1]
        if model == "gpt-5.4":
            return _FakeProc(stdout="model is not supported", returncode=1)
        else:
            Path(out_file).write_text(json.dumps({"verdict": "pass"}))
            return _FakeProc(stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = call_codex(
        prompt="hi",
        schema_path=schema_path,
        model="gpt-5.4",
        fallback_model="gpt-5.4-mini",
        timeout_s=42,
    )
    assert calls == ["gpt-5.4", "gpt-5.4-mini"]
    assert timeouts == [42, 42]  # timeout_s preserved through recursive fallback
    assert result.parsed == {"verdict": "pass"}


def test_call_codex_fails_fast_on_subprocess_error_not_model(monkeypatch, tmp_path):
    schema_path = _make_schema(tmp_path)

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        return _FakeProc(stdout="", stderr="permission denied", returncode=2)

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(CcError) as exc_info:
        call_codex(prompt="hi", schema_path=schema_path, fallback_model=None)
    assert exc_info.value.kind == "subprocess_failure"


def test_extract_token_counts_parses_last_usage_event():
    events = [
        {"type": "start"},
        {"type": "usage", "input_tokens": 111, "output_tokens": 222},
        {"type": "end"},
    ]
    tin, tout = _extract_token_counts(events)
    assert tin == 111
    assert tout == 222


def test_generator_schema_is_valid_json_schema():
    from jsonschema import Draft202012Validator
    from rubric.io import PROJECT_ROOT
    schema_path = PROJECT_ROOT / "scripts" / "rubric" / "schemas" / "generator-output.schema.json"
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)  # raises if invalid


def test_judge_schema_is_valid_json_schema():
    from jsonschema import Draft202012Validator
    from rubric.io import PROJECT_ROOT
    schema_path = PROJECT_ROOT / "scripts" / "rubric" / "schemas" / "judge-output.schema.json"
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)


def test_generator_prompt_template_exists_and_has_placeholders():
    from rubric.io import PROJECT_ROOT
    tpl = (PROJECT_ROOT / "scripts" / "rubric" / "prompts" / "generator.md").read_text()
    for placeholder in ["{rule_yaml_snapshot}", "{probe_intent}", "{case_id}",
                        "{slice}", "{track}", "{target_rule_id}",
                        "{field_reference_table}"]:
        assert placeholder in tpl, f"missing placeholder {placeholder}"


def test_judge_prompt_template_exists_and_has_placeholders():
    from rubric.io import PROJECT_ROOT
    tpl = (PROJECT_ROOT / "scripts" / "rubric" / "prompts" / "judge.md").read_text()
    for placeholder in ["{case_fixture_json}", "{derived_is_nra}", "{findings_json}",
                        "{engine_error_or_none}", "{slice}", "{filtered_criteria_yaml}"]:
        assert placeholder in tpl, f"missing placeholder {placeholder}"


from rubric.generate import (
    generate_missing,
    render_generator_prompt,
    detect_pii_shaped_strings,
)


def test_render_generator_prompt_substitutes_all_placeholders(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "stem_opt.yaml").write_text("""
version: "0.1.0"
rules:
  - id: sample
    track: stem_opt
    type: logic
    conditions: []
    severity: info
    finding: {title: T, action: A, consequence: C}
""")
    spec = CaseSpec(
        case_id="A-stem_opt-sample-pos",
        slice="A",
        track="stem_opt",
        target_rule_id="sample",
        target_rule_snapshot={"id": "sample", "conditions": []},
        probe_intent="engine MUST fire sample",
        gen_strategy="llm",
    )
    rendered = render_generator_prompt(spec, rules_dir=rules_dir)
    # All placeholders replaced
    assert "{rule_yaml_snapshot}" not in rendered
    assert "{probe_intent}" not in rendered
    assert "sample" in rendered
    assert "engine MUST fire sample" in rendered


def test_detect_pii_shaped_strings_finds_ssn_pattern():
    cases = detect_pii_shaped_strings({"answers": {"note": "SSN: 123-45-6789"}})
    assert any("ssn" in c.lower() for c in cases)


def test_detect_pii_shaped_strings_finds_a_number_pattern():
    cases = detect_pii_shaped_strings({"extraction_a": {"alien_number": "A123456789"}})
    assert any("a-number" in c.lower() or "alien" in c.lower() for c in cases)


def test_detect_pii_shaped_strings_clean_case_returns_empty():
    cases = detect_pii_shaped_strings({
        "answers": {"stage": "stem_opt", "employer": "Frogworks LLC"},
    })
    assert cases == []


def test_generate_missing_skips_existing_fixtures(tmp_path, monkeypatch):
    """If a fixture already exists on disk, generate_missing must not call codex."""
    fixture_dir = tmp_path / "rubric_fixtures"
    fixture_dir.mkdir()

    spec = CaseSpec(
        case_id="A-stem_opt-sample-pos",
        slice="A",
        track="stem_opt",
        target_rule_id="sample",
        target_rule_snapshot={"id": "sample"},
        probe_intent="test",
        gen_strategy="llm",
    )

    (fixture_dir / "A-stem_opt-sample-pos.json").write_text(json.dumps({
        "case_id": "A-stem_opt-sample-pos", "slice": "A", "track": "stem_opt",
        "target_rule_id": "sample", "probe_intent": "test",
        "generated_by": "hand", "generated_at": "2026-04-10T00:00:00Z",
        "generator_prompt_hash": None, "flavor_hint": None,
        "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        "expected": {"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                     "expected_nra": "no", "expected_track": "stem_opt", "notes": ""},
    }))

    def fail_if_called(**kwargs):
        raise AssertionError("codex should not have been called")

    monkeypatch.setattr("rubric.generate.call_codex", fail_if_called)
    new_count, skip_count, warnings = generate_missing(
        [spec], fixture_dir=fixture_dir, rules_dir=tmp_path / "rules",
    )
    assert new_count == 0
    assert skip_count == 1


def test_generate_missing_writes_new_fixture(tmp_path, monkeypatch):
    fixture_dir = tmp_path / "rubric_fixtures"
    fixture_dir.mkdir()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "stem_opt.yaml").write_text("version: 0.1.0\nrules: []\n")

    spec = CaseSpec(
        case_id="A-stem_opt-sample-pos",
        slice="A",
        track="stem_opt",
        target_rule_id="sample",
        target_rule_snapshot={"id": "sample", "conditions": []},
        probe_intent="test",
        gen_strategy="llm",
    )

    fake_output = {
        "input": {
            "answers": {"stage": "stem_opt", "years_in_us": 3},
            "extraction_a": {},
            "extraction_b": {},
            "comparisons": {},
        },
        "expected": {
            "must_fire_rule_ids": ["sample"],
            "must_not_fire_rule_ids": [],
            "expected_nra": "yes",
            "expected_track": "stem_opt",
            "notes": "",
        },
        "flavor_hint": "playful",
    }

    def fake_call(**kwargs):
        return CodexCallResult(
            text=json.dumps(fake_output),
            parsed=fake_output,
            tokens_in=10,
            tokens_out=5,
            latency_ms=0,
            raw_events=[],
            attempts=1,
        )

    monkeypatch.setattr("rubric.generate.call_codex", fake_call)
    new_count, skip_count, warnings = generate_missing(
        [spec], fixture_dir=fixture_dir, rules_dir=rules_dir,
    )
    assert new_count == 1
    assert skip_count == 0
    written = json.loads((fixture_dir / "A-stem_opt-sample-pos.json").read_text())
    assert written["input"]["answers"]["stage"] == "stem_opt"
    assert written["generated_by"].startswith("codex-cli")


def test_generate_missing_writes_sentinel_on_codex_error(tmp_path, monkeypatch):
    """When call_codex raises, generate_missing writes a sentinel fixture
    with a last_error block and records a warning, so subsequent runs skip
    the failed case unless explicitly regenerated."""
    fixture_dir = tmp_path / "rubric_fixtures"
    fixture_dir.mkdir()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "stem_opt.yaml").write_text("version: 0.1.0\nrules: []\n")

    spec = CaseSpec(
        case_id="A-stem_opt-failing-pos",
        slice="A",
        track="stem_opt",
        target_rule_id="failing",
        target_rule_snapshot={"id": "failing", "conditions": []},
        probe_intent="engine must fire failing",
        gen_strategy="llm",
    )

    from rubric.models import CodexCallError

    def boom(**kwargs):
        raise CodexCallError(
            kind="schema_violation",
            message="output violates schema: missing required field 'expected'",
        )

    monkeypatch.setattr("rubric.generate.call_codex", boom)
    new_count, skip_count, warnings = generate_missing(
        [spec], fixture_dir=fixture_dir, rules_dir=rules_dir,
    )

    # Sentinel write path: nothing counted as new or skip, one warning, sentinel on disk
    assert new_count == 0
    assert skip_count == 0
    assert len(warnings) == 1
    assert "schema_violation" in warnings[0]
    assert "A-stem_opt-failing-pos" in warnings[0]

    written = json.loads((fixture_dir / "A-stem_opt-failing-pos.json").read_text())
    assert written["last_error"]["kind"] == "schema_violation"
    assert "GENERATION FAILED" in written["expected"]["notes"]
    assert written["generated_by"].startswith("codex-cli")


def test_fixture_record_from_dict_tolerates_extra_keys():
    """FixtureRecord.from_dict must silently drop unknown keys so sentinel
    fixtures (with `last_error`) can be loaded without crashing."""
    from rubric.models import FixtureRecord
    d = {
        "case_id": "A-stem_opt-failing-pos",
        "slice": "A",
        "track": "stem_opt",
        "target_rule_id": "failing",
        "probe_intent": "x",
        "generated_by": "codex-cli/gpt-5.4",
        "generated_at": "2026-04-10T00:00:00Z",
        "generator_prompt_hash": "abc",
        "flavor_hint": None,
        "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        "expected": {"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                     "expected_nra": "no", "expected_track": "stem_opt", "notes": ""},
        "last_error": {"kind": "schema_violation", "message": "bad"},  # extra key
    }
    record = FixtureRecord.from_dict(d)
    assert record.case_id == "A-stem_opt-failing-pos"
    # last_error was dropped (not stored on the dataclass)
    assert not hasattr(record, "last_error")


def test_criteria_yaml_loads_and_filters_by_slice():
    from rubric.io import CONFIG_RUBRIC_DIR
    criteria_path = CONFIG_RUBRIC_DIR / "criteria.yaml"
    data = yaml.safe_load(criteria_path.read_text())
    assert data["version"] == "0.1.0"
    assert len(data["criteria"]) == 11

    # Verify filtering works — slice A should include positive_case_fires_target_rule
    a_criteria = [c for c in data["criteria"] if "A" in c["applies_to"]]
    a_ids = {c["id"] for c in a_criteria}
    assert "positive_case_fires_target_rule" in a_ids
    assert "negative_case_does_not_fire_target_rule" not in a_ids  # B only

    # Slice C should include operator_behavior_correct
    c_ids = {c["id"] for c in data["criteria"] if "C" in c["applies_to"]}
    assert "operator_behavior_correct" in c_ids


def test_rubric_version_file_exists():
    from rubric.io import CONFIG_RUBRIC_DIR
    assert (CONFIG_RUBRIC_DIR / "rubric_version.txt").read_text().strip() == "0.1.0"


def test_all_hard_fail_criteria_exist_in_criteria_list():
    from rubric.io import CONFIG_RUBRIC_DIR
    data = yaml.safe_load((CONFIG_RUBRIC_DIR / "criteria.yaml").read_text())
    all_ids = {c["id"] for c in data["criteria"]}
    for hfc in data["scoring"]["hard_fail_criteria"]:
        assert hfc in all_ids, f"hard_fail_criterion {hfc} not in criteria list"


def test_filter_criteria_for_slice_a_includes_correct_subset():
    criteria = [
        {"id": "c1", "applies_to": ["A", "B"], "description": "x"},
        {"id": "c2", "applies_to": ["C"], "description": "y"},
        {"id": "c3", "applies_to": ["A"], "description": "z"},
    ]
    filtered = filter_criteria_for_slice(criteria, "A")
    ids = {c["id"] for c in filtered}
    assert ids == {"c1", "c3"}


def test_compute_judge_cache_key_stable_across_equal_inputs():
    input_hash = "a" * 64
    findings_hash = "b" * 64
    rubric_version = "0.1.0"
    prompt_hash = "c" * 64
    k1 = compute_judge_cache_key(input_hash, findings_hash, rubric_version, prompt_hash)
    k2 = compute_judge_cache_key(input_hash, findings_hash, rubric_version, prompt_hash)
    assert k1 == k2


def test_compute_judge_cache_key_changes_on_rubric_version_bump():
    args = ("a" * 64, "b" * 64, "0.1.0", "c" * 64)
    k1 = compute_judge_cache_key(*args)
    k2 = compute_judge_cache_key("a" * 64, "b" * 64, "0.2.0", "c" * 64)
    assert k1 != k2


def test_judge_case_uses_cache_on_second_call(tmp_path, monkeypatch):
    fixture = _make_fixture(
        case_id="A-stem_opt-test-pos",
        track="stem_opt",
        input_={"answers": {"stage": "stem_opt", "years_in_us": 3},
                "extraction_a": {}, "extraction_b": {},
                "comparisons": {"job_title": {"status": "mismatch", "confidence": 0.9}}},
        expected={"must_fire_rule_ids": ["job_title_mismatch"], "must_not_fire_rule_ids": [],
                  "expected_nra": "yes", "expected_track": "stem_opt", "notes": ""},
    )
    eval_record = evaluate_case(fixture, cache_dir=tmp_path / "eval")

    call_count = {"n": 0}

    def fake_call(**kwargs):
        call_count["n"] += 1
        return CodexCallResult(
            text=json.dumps({
                "verdict": "pass",
                "subscores": {
                    "categorization": {"score": 1.0, "criteria_applied": ["track_selection_correct"], "note": "ok"},
                    "findings": {"score": 1.0, "criteria_applied": ["positive_case_fires_target_rule"], "note": "ok"},
                },
                "flags": [],
            }),
            parsed={
                "verdict": "pass",
                "subscores": {
                    "categorization": {"score": 1.0, "criteria_applied": ["track_selection_correct"], "note": "ok"},
                    "findings": {"score": 1.0, "criteria_applied": ["positive_case_fires_target_rule"], "note": "ok"},
                },
                "flags": [],
            },
            tokens_in=10, tokens_out=5, latency_ms=0, raw_events=[], attempts=1,
        )

    monkeypatch.setattr("rubric.judge.call_codex", fake_call)

    record1 = judge_case(fixture, eval_record, cache_dir=tmp_path / "judge")
    assert record1.verdict == "pass"
    assert call_count["n"] == 1

    record2 = judge_case(fixture, eval_record, cache_dir=tmp_path / "judge")
    assert record2.verdict == "pass"
    assert call_count["n"] == 1  # cache hit, no second call


def test_render_judge_prompt_substitutes_all_placeholders(tmp_path):
    fixture = _make_fixture(
        case_id="A-stem_opt-test-pos",
        track="stem_opt",
        input_={"answers": {"stage": "stem_opt"}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        expected={"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                  "expected_nra": "yes", "expected_track": "stem_opt", "notes": ""},
    )
    eval_record = EvalRecord(
        case_id="A-stem_opt-test-pos",
        engine_version="1.0.0",
        rule_file_path="config/rules/stem_opt.yaml",
        rule_file_hash="abc",
        input_hash="def",
        evaluated_at="2026-04-10T00:00:00Z",
        derived={"is_nra": "yes"},
        findings=[{"rule_id": "job_title_mismatch", "severity": "warning", "category": "comparison",
                   "title": "t", "action": "a", "consequence": "c", "immigration_impact": True}],
    )
    prompt = render_judge_prompt(fixture, eval_record)
    assert "{case_fixture_json}" not in prompt
    assert "{findings_json}" not in prompt
    assert "job_title_mismatch" in prompt
    assert "is_nra: yes" in prompt


from rubric.aggregate import (
    assemble_scorecard,
    compute_totals,
    classify_verdict_from_subscores,
)


def test_classify_verdict_pass_at_threshold():
    subscores = {
        "categorization": {"score": 0.95, "criteria_applied": ["track_selection_correct"], "note": ""},
        "findings": {"score": 0.95, "criteria_applied": ["positive_case_fires_target_rule"], "note": ""},
    }
    weights = {"categorization": 1.0, "findings": 2.0}
    hard_fail = []
    verdict = classify_verdict_from_subscores(subscores, weights, hard_fail, pass_t=0.90, partial_t=0.60)
    assert verdict == "pass"


def test_classify_verdict_fail_on_hard_fail_criterion():
    subscores = {
        "findings": {"score": 0.0, "criteria_applied": ["positive_case_fires_target_rule"], "note": ""},
    }
    weights = {"findings": 2.0}
    hard_fail = ["positive_case_fires_target_rule"]
    verdict = classify_verdict_from_subscores(subscores, weights, hard_fail, pass_t=0.90, partial_t=0.60)
    assert verdict == "fail"


def test_classify_verdict_partial_range():
    subscores = {
        "findings": {"score": 0.70, "criteria_applied": [], "note": ""},
    }
    weights = {"findings": 1.0}
    verdict = classify_verdict_from_subscores(subscores, weights, [], pass_t=0.90, partial_t=0.60)
    assert verdict == "partial"


def test_compute_totals_counts_verdicts():
    judge_records = [
        JudgeRecord(cache_key="1", cache_key_inputs={}, case_id="c1", judged_at="",
                    judged_by="", verdict="pass", subscores={}),
        JudgeRecord(cache_key="2", cache_key_inputs={}, case_id="c2", judged_at="",
                    judged_by="", verdict="pass", subscores={}),
        JudgeRecord(cache_key="3", cache_key_inputs={}, case_id="c3", judged_at="",
                    judged_by="", verdict="fail", subscores={}),
    ]
    totals = compute_totals(judge_records)
    assert totals["pass"] == 2
    assert totals["fail"] == 1
    assert totals["cases"] == 3


def test_assemble_scorecard_produces_complete_dict(tmp_path):
    cases = [CaseSpec(
        case_id="A-stem_opt-test-pos", slice="A", track="stem_opt",
        target_rule_id="test", probe_intent="", gen_strategy="llm",
    )]
    eval_records = {"A-stem_opt-test-pos": EvalRecord(
        case_id="A-stem_opt-test-pos", engine_version="1.0.0",
        rule_file_path="x", rule_file_hash="y", input_hash="z",
        evaluated_at="2026-04-10T00:00:00Z", derived={"is_nra": "yes"},
        findings=[],
    )}
    judge_records = {"A-stem_opt-test-pos": JudgeRecord(
        cache_key="k", cache_key_inputs={}, case_id="A-stem_opt-test-pos",
        judged_at="2026-04-10T00:00:00Z", judged_by="codex", verdict="pass",
        subscores={"findings": {"score": 1.0, "criteria_applied": [], "note": ""}},
    )}
    telemetry = CallTelemetry(generator_calls=1, judge_calls=1)
    sc = assemble_scorecard(
        cases=cases,
        eval_records=eval_records,
        judge_records=judge_records,
        telemetry=telemetry,
        warnings=[],
        prior_scorecard=None,
    )
    assert sc.totals["cases"] == 1
    assert sc.totals["pass"] == 1
    assert sc.by_track["stem_opt"]["pass"] == 1
    assert sc.by_slice["A"]["pass"] == 1


def test_rubric_loop_cli_help():
    proc = subprocess.run(
        ["python", "scripts/rubric_loop.py", "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "--phases" in proc.stdout
    assert "--only" in proc.stdout
    assert "--regen" in proc.stdout
    assert "--slice" in proc.stdout


def test_rubric_loop_discover_only_runs(tmp_path):
    """Discover phase should succeed against the real repo rules/goldens."""
    proc = subprocess.run(
        ["python", "scripts/rubric_loop.py", "--phases", "discover"],
        capture_output=True, text=True,
    )
    # Should exit 0 (discovery works) regardless of generator/judge state
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "manifest" in (proc.stdout + proc.stderr).lower()


def test_meta_broken_rule_is_flagged_as_fail(tmp_path, monkeypatch):
    """The highest-value single test: if a rule is contradictory, the loop must
    detect that slice-A positive cases can't fire it and mark them fail.

    If this test ever passes without the fail being recorded, the rubric loop
    is silently broken and should not be trusted.
    """
    broken_rules_src = Path(__file__).parent / "fixtures" / "broken_rules.yaml"
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "broken_rules.yaml").write_text(broken_rules_src.read_text())
    goldens_dir = tmp_path / "goldens"
    goldens_dir.mkdir()

    # Build manifest — should have A+B for impossible_rule
    manifest = build_manifest(rules_dir, goldens_dir)
    assert len(manifest) == 2
    a_case = next(c for c in manifest if c.slice == "A")
    b_case = next(c for c in manifest if c.slice == "B")

    # Fake generator: produces a syntactically valid case that can't satisfy
    # the impossible conditions (stage can only have one value at a time).
    def fake_gen_call(**kwargs):
        return CodexCallResult(
            text=json.dumps({
                "input": {
                    "answers": {"stage": "f1_student"},
                    "extraction_a": {}, "extraction_b": {}, "comparisons": {},
                },
                "expected": {
                    "must_fire_rule_ids": ["impossible_rule"],
                    "must_not_fire_rule_ids": [],
                    "expected_nra": "yes",
                    "expected_track": "stem_opt",
                    "notes": "generator attempted but cannot satisfy mutually exclusive conditions",
                },
                "flavor_hint": None,
            }),
            parsed={
                "input": {
                    "answers": {"stage": "f1_student"},
                    "extraction_a": {}, "extraction_b": {}, "comparisons": {},
                },
                "expected": {
                    "must_fire_rule_ids": ["impossible_rule"],
                    "must_not_fire_rule_ids": [],
                    "expected_nra": "yes",
                    "expected_track": "stem_opt",
                    "notes": "",
                },
                "flavor_hint": None,
            },
            tokens_in=5, tokens_out=5, latency_ms=0, raw_events=[], attempts=1,
        )

    monkeypatch.setattr("rubric.generate.call_codex", fake_gen_call)
    fixture_dir = tmp_path / "rubric_fixtures"
    generate_missing([a_case], fixture_dir=fixture_dir, rules_dir=rules_dir)

    # Phase 2: run the real engine on the fake fixture
    fixture = FixtureRecord.from_dict(
        json.loads((fixture_dir / f"{a_case.case_id}.json").read_text())
    )
    # Monkeypatch CONFIG_RULES_DIR so evaluate looks in tmp_path/rules
    monkeypatch.setattr("rubric.evaluate.CONFIG_RULES_DIR", rules_dir)
    eval_record = evaluate_case(fixture, cache_dir=tmp_path / "eval_cache")
    # Engine must return no findings — the rule is impossible
    assert not any(f["rule_id"] == "impossible_rule" for f in eval_record.findings)

    # Phase 3: simulate a judge that applies the hard-fail rule correctly
    def fake_judge_call(**kwargs):
        return CodexCallResult(
            text=json.dumps({
                "verdict": "fail",
                "subscores": {
                    "findings": {
                        "score": 0.0,
                        "criteria_applied": ["positive_case_fires_target_rule"],
                        "note": "impossible_rule did not fire; its conditions are mutually exclusive (stage cannot be both f1_student and h1b)",
                    },
                },
                "flags": ["contradictory-rule-conditions"],
            }),
            parsed={
                "verdict": "fail",
                "subscores": {
                    "findings": {
                        "score": 0.0,
                        "criteria_applied": ["positive_case_fires_target_rule"],
                        "note": "impossible_rule did not fire",
                    },
                },
                "flags": ["contradictory-rule-conditions"],
            },
            tokens_in=5, tokens_out=5, latency_ms=0, raw_events=[], attempts=1,
        )

    monkeypatch.setattr("rubric.judge.call_codex", fake_judge_call)
    judge_record = judge_case(fixture, eval_record, cache_dir=tmp_path / "judge_cache")

    # The meta-assertion: fail verdict + hard-fail criterion cited
    assert judge_record.verdict == "fail"
    assert "positive_case_fires_target_rule" in judge_record.subscores["findings"]["criteria_applied"]
    assert "contradictory-rule-conditions" in judge_record.flags
