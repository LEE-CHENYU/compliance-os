"""Dataclasses shared across the rubric loop phases."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CaseSpec:
    """An entry in the case manifest — one case to run through the loop."""
    case_id: str
    slice: str                       # "A" | "B" | "C" | "D" | "E"
    track: str
    target_rule_id: str | None = None
    target_rule_snapshot: dict | None = None
    probe_intent: str = ""
    gen_strategy: str = "llm"        # "llm" | "golden"
    fixture_content: dict | None = None   # pre-loaded goldens
    flavor_hint: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> CaseSpec:
        return cls(**d)


@dataclass
class FixtureRecord:
    """What Phase 1 writes to scripts/rubric_fixtures/<case_id>.json."""
    case_id: str
    slice: str
    track: str
    target_rule_id: str | None
    probe_intent: str
    generated_by: str                # "codex-cli@<ver>/<model>" or "hand"
    generated_at: str                # ISO timestamp
    generator_prompt_hash: str | None
    flavor_hint: str | None
    input: dict                      # {answers, extraction_a, extraction_b, comparisons}
    expected: dict                   # {must_fire_rule_ids, must_not_fire_rule_ids, expected_nra, expected_track, notes}

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FixtureRecord:
        return cls(**d)


@dataclass
class EvalRecord:
    """What Phase 2 writes to scripts/rubric_cache/evaluate/<case_id>.json."""
    case_id: str
    engine_version: str
    rule_file_path: str
    rule_file_hash: str
    input_hash: str
    evaluated_at: str
    derived: dict                    # {"is_nra": "yes"|"no"}
    findings: list[dict]             # serialized FindingResult list
    engine_error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> EvalRecord:
        return cls(**d)


@dataclass
class JudgeRecord:
    """What Phase 3 writes to scripts/rubric_cache/judge/<cache_key>.json."""
    cache_key: str
    cache_key_inputs: dict
    case_id: str
    judged_at: str
    judged_by: str
    verdict: str                     # "pass" | "partial" | "fail" | "unrunnable"
    subscores: dict                  # {dimension: {score, criteria_applied, note}}
    flags: list[str] = field(default_factory=list)
    raw_judge_output: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> JudgeRecord:
        return cls(**d)


@dataclass
class Scorecard:
    """What Phase 4 writes to out/rubric-loop-<ts>.{json,md}."""
    run_id: str
    engine_version: str
    rubric_version: str
    codex_version: str
    codex_model: str
    reasoning_effort: str
    started_at: str
    completed_at: str
    totals: dict
    by_track: dict
    by_slice: dict
    by_dimension: dict
    failures: list[dict]
    coverage_gaps: list[str]
    warnings: list[str]
    delta_from_last_run: dict
    telemetry: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CallTelemetry:
    """Per-run accounting for codex calls + tokens. No cost estimation —
    codex CLI usage is subscription-billed, not metered."""
    generator_calls: int = 0
    generator_calls_cached: int = 0
    judge_calls: int = 0
    judge_calls_cached: int = 0
    tokens_in_total: int = 0
    tokens_out_total: int = 0


@dataclass
class CodexCallResult:
    """Successful `codex exec` call outcome."""
    text: str                        # raw JSON string from --output-last-message
    parsed: dict                     # json.loads of text
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int
    raw_events: list[dict] = field(default_factory=list)
    attempts: int = 1


class CodexCallError(Exception):
    """Raised when `codex exec` cannot produce a valid result after retries."""
    def __init__(self, kind: str, message: str, stderr: str = "", attempts: int = 1):
        super().__init__(message)
        self.kind = kind                 # "timeout"|"parse_failure"|"schema_violation"|"subprocess_failure"
        self.message = message
        self.stderr = stderr
        self.attempts = attempts


class CoverageGap(Exception):
    """Raised when Phase 0 detects a rule with no covering case in the manifest."""
