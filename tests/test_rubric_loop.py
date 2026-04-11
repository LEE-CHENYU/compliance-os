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
    restored = CaseSpec.from_dict(d)
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
