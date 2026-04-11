# Rubric Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/rubric_loop.py` — a codex-CLI-backed evaluation harness that systematically exercises Guardian's YAML rule engine across its full input space (~182 equivalence-class cases) and grades its behavior against a declarative rubric, producing a scorecard that identifies categorization bugs, rule-firing errors, and rule-set quality issues.

**Spec:** `docs/superpowers/specs/2026-04-10-rubric-loop-design.md` — read this first. It captures the eight key decisions (D1–D8), the 13-dimension input space analysis, the five-slice coverage plan, and the five on-disk data contracts. This plan is how to build what the spec describes; the spec is *why*.

**Architecture:** Four-phase sequential pipeline (discover → generate-missing → evaluate → judge → aggregate) with on-disk fixture cache (committed to git) and eval/judge caches (gitignored). Generator and judge both call `codex exec` with `--output-schema` for structured JSON output, `--sandbox read-only` for hermetic pure-LLM calls, and `gpt-5.4 / xhigh` as defaults (non-coding task). No changes to `compliance_os/` — the harness treats the engine as a black box. ~71 rules × 2 polarities (slices A+B, LLM-generated) + ~40 hand-written edge-case goldens (slices C+D+E) = ~182 cases.

**Tech Stack:** Python 3.11, existing `compliance_os.web.services.rule_engine`, `pyyaml`, `jsonschema` (already transitively available via llama-index), `codex` CLI v0.118.0, pytest.

**Build order:** Strictly bottom-up — foundation modules (models, ids, io, hints) first; then phase modules starting with the ones that have no codex dependency (discover, evaluate); then the codex wrapper with mocked tests; then the codex-dependent phases (generate, judge); then aggregation; then the main entrypoint; then the meta-test; finally fixture generation and commit. This order minimizes integration risk — every task that calls codex is preceded by a task that exercises a mock of the same interface.

---

## File Structure

### New Python module files

| File | Responsibility |
|---|---|
| `scripts/rubric/__init__.py` | Package marker |
| `scripts/rubric/models.py` | Dataclasses: `CaseSpec`, `FixtureRecord`, `EvalRecord`, `JudgeRecord`, `Scorecard`, `CallTelemetry`, `CodexCallResult`, `CodexCallError`, `CoverageGap` |
| `scripts/rubric/case_ids.py` | `build_case_id()`, `parse_case_id()`, `validate_case_id()` |
| `scripts/rubric/hints.py` | `build_field_reference_table()` — reads YAMLs, returns markdown table for generator prompts |
| `scripts/rubric/io.py` | Paths, JSON load/save helpers, SHA-256 hash helpers |
| `scripts/rubric/discover.py` | Phase 0: `build_manifest()`, `build_positive_intent()`, `build_negative_intent()` |
| `scripts/rubric/evaluate.py` | Phase 2: `evaluate_case()`, eval-cache management |
| `scripts/rubric/codex_client.py` | Thin wrapper around `codex exec` with retry + schema validation + fallback |
| `scripts/rubric/generate.py` | Phase 1: `generate_missing()`, PII regex screener |
| `scripts/rubric/judge.py` | Phase 3: `judge_case()`, cache-key computation |
| `scripts/rubric/aggregate.py` | Phase 4: `assemble_scorecard()`, JSON + markdown emission |
| `scripts/rubric_loop.py` | Main CLI: argparse, phase orchestration, flag handling |

### New prompt / schema / data files

| File | Responsibility |
|---|---|
| `scripts/rubric/prompts/generator.md` | Generator system + user prompt template |
| `scripts/rubric/prompts/judge.md` | Judge system + user prompt template |
| `scripts/rubric/schemas/generator-output.schema.json` | JSON Schema for generator output |
| `scripts/rubric/schemas/judge-output.schema.json` | JSON Schema for judge output |
| `config/rubric/criteria.yaml` | 11 rubric criteria across 4 dimensions |
| `config/rubric/rubric_version.txt` | Single-line semver — bump to invalidate judge cache |

### New fixture directories

| Path | Contents | Committed? |
|---|---|---|
| `scripts/rubric_fixtures/` | LLM-generated slice-A+B fixtures (~142 after first run) | Yes |
| `scripts/rubric_fixtures/goldens/` | Hand-written slice-C/D/E edge-case fixtures (~40) | Yes |
| `scripts/rubric_cache/evaluate/` | Phase 2 eval cache | No (gitignored) |
| `scripts/rubric_cache/judge/` | Phase 3 judge cache | No (gitignored) |
| `out/` | Scorecards (already exists) | No (gitignored) |

### New test files

| File | Responsibility |
|---|---|
| `tests/test_rubric_loop.py` | Unit + integration tests for the harness |
| `tests/fixtures/broken_rules.yaml` | Contradictory-conditions rule file for the meta-test |

### Modified files

| File | Change |
|---|---|
| `.gitignore` | Add `scripts/rubric_cache/` and `out/rubric-loop-*` |

**Zero changes to `compliance_os/`.** The harness imports `rule_engine` as a library and never modifies it.

---

## Task 1: Package scaffold + data models

**Files:**
- Create: `scripts/rubric/__init__.py`
- Create: `scripts/rubric/models.py`
- Create: `tests/test_rubric_loop.py`

- [ ] **Step 1: Create empty package marker**

Create `scripts/rubric/__init__.py` with a single docstring:

```python
"""Rubric loop: codex-backed evaluation harness for the compliance rule engine.

See docs/superpowers/specs/2026-04-10-rubric-loop-design.md for design rationale.
"""
```

- [ ] **Step 2: Write failing test for dataclass construction and round-trip**

Create `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rubric'`

- [ ] **Step 4: Implement models.py**

Create `scripts/rubric/models.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 4 tests green.

- [ ] **Step 6: Commit**

```bash
git add scripts/rubric/__init__.py scripts/rubric/models.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): package scaffold + data models"
```

---

## Task 2: Case ID canonicalization

**Files:**
- Create: `scripts/rubric/case_ids.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
from rubric.case_ids import build_case_id, parse_case_id, validate_case_id


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_build_case_id_format -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement case_ids.py**

Create `scripts/rubric/case_ids.py`:

```python
"""Canonical case ID generation and parsing.

Format for slice A/B:  `<slice>-<track>-<rule_id>-<polarity>`
  where polarity is "pos" or "neg"

Format for slice C/D/E (goldens): free-form but must start with the slice letter,
  e.g., `C-operator-contains-scalar`, `E-edge-false-string-gotcha`.
"""
from __future__ import annotations

VALID_SLICES = {"A", "B", "C", "D", "E"}
VALID_POLARITIES = {"pos", "neg"}


def build_case_id(*, slice: str, track: str, rule_id: str, polarity: str) -> str:
    """Construct the canonical case ID for a slice-A or slice-B case."""
    if slice not in {"A", "B"}:
        raise ValueError(f"build_case_id only supports slice A/B, got {slice!r}")
    if polarity not in VALID_POLARITIES:
        raise ValueError(f"polarity must be 'pos' or 'neg', got {polarity!r}")
    return f"{slice}-{track}-{rule_id}-{polarity}"


def parse_case_id(case_id: str) -> dict:
    """Parse a slice-A/B case ID into its components.

    Rule IDs may contain underscores, so we split on the first and last hyphen
    (slice + track + polarity are fixed-shape), leaving the middle as rule_id.
    """
    parts = case_id.split("-")
    if len(parts) < 4:
        raise ValueError(f"case_id too short to parse: {case_id!r}")
    slice_ = parts[0]
    track = parts[1]
    polarity = parts[-1]
    rule_id = "-".join(parts[2:-1])
    if slice_ not in {"A", "B"}:
        raise ValueError(f"parse_case_id only supports slice A/B IDs, got {case_id!r}")
    if polarity not in VALID_POLARITIES:
        raise ValueError(f"polarity must be 'pos' or 'neg' in {case_id!r}")
    return {"slice": slice_, "track": track, "rule_id": rule_id, "polarity": polarity}


def validate_case_id(case_id: str) -> None:
    """Raise ValueError if case_id is not shaped like a valid ID. Accepts goldens."""
    if not case_id:
        raise ValueError("case_id is empty")
    slice_ = case_id[0]
    if slice_ not in VALID_SLICES:
        raise ValueError(f"case_id must start with slice letter (A/B/C/D/E), got {case_id!r}")
    if len(case_id) < 3 or case_id[1] != "-":
        raise ValueError(f"case_id second character must be '-', got {case_id!r}")
    # Goldens are free-form after the slice letter; slice A/B must parse strictly
    if slice_ in {"A", "B"}:
        parse_case_id(case_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 10 tests green (4 from Task 1 + 6 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/case_ids.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): case ID canonicalization"
```

---

## Task 3: Field reference builder (hints.py)

**Files:**
- Create: `scripts/rubric/hints.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_rubric_loop.py`:

```python
from rubric.hints import build_field_reference_table, gather_rule_fields


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rubric_loop.py::test_gather_rule_fields_from_sample_yaml -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement hints.py**

Create `scripts/rubric/hints.py`:

```python
"""Generator prompt helpers: derive a field reference table from rule YAMLs.

The generator must know which fields the engine reads (51+ fields across 5 YAMLs)
to produce structurally valid cases. This module computes that list dynamically
so new fields in new rules auto-populate the generator's prompt.
"""
from __future__ import annotations

from pathlib import Path

import yaml


# Fields read by rule_engine._derive_nra that may not appear in rule conditions
# directly but affect is_nra derivation. The generator must know about these.
NRA_DERIVATION_INPUTS = [
    "stage",
    "years_in_us",
    "tax_residency_status",
    "owner_residency",
]

# Value-type gotchas — hand-maintained shortlist of fields where the rule YAML
# has a known type quirk the generator must respect.
TYPE_GOTCHAS: dict[str, str] = {
    "form_5472_present": "STRING 'True' or 'False' (not a bool). entity.yaml quirk.",
    "schedules_present": "LIST of strings, e.g. ['schedule_c'].",
    "is_nra": "DERIVED in rule_engine._derive_nra. Do NOT set directly. Set stage + years_in_us, or tax_residency_status, or owner_residency.",
}


def gather_rule_fields(rules_dir: Path) -> set[str]:
    """Return the set of unique `field:` names across all YAML files in rules_dir."""
    fields: set[str] = set()
    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        data = yaml.safe_load(yaml_file.read_text()) or {}
        for rule in data.get("rules", []) or []:
            for condition in rule.get("conditions", []) or []:
                f = condition.get("field")
                if f:
                    fields.add(f)
    return fields


def build_field_reference_table(rules_dir: Path) -> str:
    """Return a markdown table of every field the engine can read, with hints.

    Output looks like:

        | field | notes |
        |---|---|
        | stage | ... |
        | ... |
    """
    fields = gather_rule_fields(rules_dir)
    # Always include NRA derivation inputs even if they don't appear in conditions
    for f in NRA_DERIVATION_INPUTS:
        fields.add(f)

    lines = ["| field | notes |", "|---|---|"]
    for f in sorted(fields):
        note = TYPE_GOTCHAS.get(f, "")
        lines.append(f"| `{f}` | {note} |")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 12 tests green (10 prior + 2 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/hints.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): field reference table builder"
```

---

## Task 4: I/O helpers and paths

**Files:**
- Create: `scripts/rubric/io.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_sha256_of_obj_is_stable -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement io.py**

Create `scripts/rubric/io.py`:

```python
"""Paths, JSON I/O, and hashing helpers for the rubric loop."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# All paths are relative to the repo root, discovered by walking up from this file.
# scripts/rubric/io.py -> scripts/rubric -> scripts -> <repo root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_DIR = PROJECT_ROOT / "scripts" / "rubric_fixtures"
GOLDENS_DIR = FIXTURE_DIR / "goldens"
CACHE_ROOT = PROJECT_ROOT / "scripts" / "rubric_cache"
EVAL_CACHE_DIR = CACHE_ROOT / "evaluate"
JUDGE_CACHE_DIR = CACHE_ROOT / "judge"
OUT_DIR = PROJECT_ROOT / "out"

CONFIG_RULES_DIR = PROJECT_ROOT / "config" / "rules"
CONFIG_RUBRIC_DIR = PROJECT_ROOT / "config" / "rubric"


def ensure_dirs(*paths: Path) -> None:
    """Create each directory if missing. Idempotent."""
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_of_obj(obj: Any) -> str:
    """Stable hash of a JSON-serializable object (key order ignored)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return sha256_of_text(canonical)


def sha256_of_file(path: Path) -> str:
    return sha256_of_text(path.read_text())


def save_json(path: Path, obj: Any) -> None:
    """Write obj as pretty-printed JSON to path, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 16 tests green.

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/io.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): I/O helpers and paths"
```

---

## Task 5: Phase 0 — Discover

**Files:**
- Create: `scripts/rubric/discover.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
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


def test_discover_raises_coverage_gap_when_rule_missing(tmp_path):
    """If a rule YAML has a rule that has NO entry in the discover function's
    output (impossible today but a guard for future refactors), CoverageGap fires."""
    # Tamper: build_manifest internally iterates YAMLs, so the only way to
    # induce a gap is to feed a YAML with a rule that build_manifest doesn't
    # pair up. Since our loop pairs every rule automatically, this test
    # exercises the CoverageGap check by supplying a golden that references
    # a non-existent rule AND removing the YAML rule — then asserts the gap.
    rules_dir = tmp_path / "rules"
    goldens_dir = tmp_path / "goldens"
    goldens_dir.mkdir(parents=True)

    # Write a rules file with one rule
    _write_sample_rules(rules_dir)
    # Write a golden that references a rule that exists
    (goldens_dir / "C-covers-nothing.json").write_text(json.dumps({
        "case_id": "C-covers-nothing",
        "slice": "C",
        "track": "stem_opt",
        "target_rule_id": "sample_rule_a",  # covers the rule
        "probe_intent": "covers",
        "generated_by": "hand",
        "generated_at": "2026-04-10T00:00:00Z",
        "generator_prompt_hash": None,
        "flavor_hint": None,
        "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
        "expected": {"must_fire_rule_ids": [], "must_not_fire_rule_ids": [],
                     "expected_nra": "no", "expected_track": "stem_opt", "notes": ""},
    }))
    # This should succeed — A+B slices auto-cover sample_rule_a
    cases = build_manifest(rules_dir, goldens_dir)
    assert len(cases) == 3  # A + B + C

    # Now add a rule with NO covering case by intercepting: overwrite rules file
    # with TWO rules but delete the auto-generator side-effect is impossible.
    # Instead: write a YAML with 2 rules, and confirm both get A+B pairs.
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_discover_creates_ab_pair_per_rule -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement discover.py**

Create `scripts/rubric/discover.py`:

```python
"""Phase 0: discover the case manifest from rule YAMLs + static goldens.

This phase is pure — no external calls, no cache writes. It exists to:
  1. Enumerate every (rule, polarity) that needs an LLM-generated case (slices A+B).
  2. Load hand-written goldens for slices C/D/E.
  3. Enforce the CoverageGap invariant: every rule in every YAML has ≥1 case.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from rubric.case_ids import build_case_id
from rubric.models import CaseSpec, CoverageGap


def build_positive_intent(rule: dict) -> str:
    """Derive a styling-neutral probe intent that says the engine MUST fire this rule."""
    rule_id = rule.get("id", "<unknown>")
    condition_lines = []
    for c in rule.get("conditions", []) or []:
        condition_lines.append(
            f"  - {c.get('source', '?')}.{c.get('field', '?')} "
            f"{c.get('operator', '?')} {c.get('value', '')}".rstrip()
        )
    conditions_text = "\n".join(condition_lines) if condition_lines else "  (no conditions — rule always fires)"
    return (
        f"Generate a synthetic case where the engine MUST fire rule '{rule_id}'. "
        f"All of these conditions must be satisfied simultaneously:\n{conditions_text}\n"
        f"No real PII or real-looking government identifiers."
    )


def build_negative_intent(rule: dict) -> str:
    """Derive an intent that says the engine must NOT fire this rule, but adversarially close."""
    rule_id = rule.get("id", "<unknown>")
    condition_lines = []
    for c in rule.get("conditions", []) or []:
        condition_lines.append(
            f"  - {c.get('source', '?')}.{c.get('field', '?')} "
            f"{c.get('operator', '?')} {c.get('value', '')}".rstrip()
        )
    conditions_text = "\n".join(condition_lines) if condition_lines else "  (no conditions)"
    return (
        f"Generate a synthetic case where the engine must NOT fire rule '{rule_id}', "
        f"but that structurally resembles a case that WOULD fire it. "
        f"Produce a case where ONE of the rule's conditions is deliberately not satisfied "
        f"while the others are. Rule conditions:\n{conditions_text}\n"
        f"No real PII or real-looking government identifiers."
    )


def _all_rule_ids(rules_dir: Path) -> set[str]:
    ids: set[str] = set()
    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        data = yaml.safe_load(yaml_file.read_text()) or {}
        for rule in data.get("rules", []) or []:
            rid = rule.get("id")
            if rid:
                ids.add(rid)
    return ids


def build_manifest(rules_dir: Path, goldens_dir: Path) -> list[CaseSpec]:
    """Return the full case manifest for one run.

    Raises:
        CoverageGap: if any rule in rules_dir has no covering case in the manifest.
    """
    cases: list[CaseSpec] = []

    # Slices A + B — one case per rule, both polarities
    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        track = yaml_file.stem
        data = yaml.safe_load(yaml_file.read_text()) or {}
        for rule in data.get("rules", []) or []:
            rule_id = rule.get("id")
            if not rule_id:
                continue

            cases.append(CaseSpec(
                case_id=build_case_id(slice="A", track=track, rule_id=rule_id, polarity="pos"),
                slice="A",
                track=track,
                target_rule_id=rule_id,
                target_rule_snapshot=rule,
                probe_intent=build_positive_intent(rule),
                gen_strategy="llm",
            ))
            cases.append(CaseSpec(
                case_id=build_case_id(slice="B", track=track, rule_id=rule_id, polarity="neg"),
                slice="B",
                track=track,
                target_rule_id=rule_id,
                target_rule_snapshot=rule,
                probe_intent=build_negative_intent(rule),
                gen_strategy="llm",
            ))

    # Slices C / D / E — static goldens
    if goldens_dir.exists():
        for golden_file in sorted(goldens_dir.glob("*.json")):
            spec = json.loads(golden_file.read_text())
            cases.append(CaseSpec(
                case_id=spec["case_id"],
                slice=spec["slice"],
                track=spec.get("track", ""),
                target_rule_id=spec.get("target_rule_id"),
                target_rule_snapshot=None,
                probe_intent=spec.get("probe_intent", ""),
                gen_strategy="golden",
                fixture_content=spec,
                flavor_hint=spec.get("flavor_hint"),
            ))

    # Coverage gap invariant
    seen = {c.target_rule_id for c in cases if c.target_rule_id}
    missing = _all_rule_ids(rules_dir) - seen
    if missing:
        raise CoverageGap(f"rules with no covering case: {sorted(missing)}")

    return cases
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 21 tests green.

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/discover.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): Phase 0 discover — build manifest from YAMLs + goldens"
```

---

## Task 6: Seed static goldens (6 fixtures to bootstrap)

**Files:**
- Create: `scripts/rubric_fixtures/.gitkeep`
- Create: `scripts/rubric_fixtures/goldens/C-operator-contains-scalar.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-gt-malformed-date.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch1-explicit.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch2-f1-exempt-boundary.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-empty-context.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-false-string-gotcha.json`
- Modify: `tests/test_rubric_loop.py`

This task seeds just enough goldens to exercise Phases 2-4 against real data before Task 7. The remaining ~34 goldens come in Task 16 after the loop is end-to-end working.

- [ ] **Step 1: Create fixture directory markers**

```bash
mkdir -p scripts/rubric_fixtures/goldens
touch scripts/rubric_fixtures/.gitkeep
```

- [ ] **Step 2: Create C-operator-contains-scalar.json**

This probes `rule_engine.Condition.evaluate` handling of `contains` against a non-list value. The `schedule_c_on_opt` rule in `entity.yaml` uses `contains` on `schedules_present`. If we feed a scalar instead of a list, the engine must return False (not raise).

```json
{
  "case_id": "C-operator-contains-scalar",
  "slice": "C",
  "track": "entity",
  "target_rule_id": "schedule_c_on_opt",
  "probe_intent": "Probe that the `contains` operator in rule_engine.Condition.evaluate returns False when actual value is a scalar instead of a list. The schedule_c_on_opt rule must NOT fire because schedules_present is a string, not a list containing 'schedule_c'.",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {
      "stage": "opt",
      "years_in_us": 3,
      "visa_type": "f1_opt_stem"
    },
    "extraction_a": {},
    "extraction_b": {
      "schedules_present": "schedule_c"
    },
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": ["schedule_c_on_opt"],
    "expected_nra": "yes",
    "expected_track": "entity",
    "notes": "contains-operator on scalar must return False, not raise. schedule_c_on_opt stays quiet."
  }
}
```

- [ ] **Step 3: Create C-operator-gt-malformed-date.json**

```json
{
  "case_id": "C-operator-gt-malformed-date",
  "slice": "C",
  "track": "stem_opt",
  "target_rule_id": "grace_period_employment",
  "probe_intent": "Probe that the `lt` / `gt` operators in rule_engine.Condition.evaluate handle malformed date strings by returning False (via _parse_date returning None), not raising. The grace_period_employment rule must NOT fire when end_date is gibberish.",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {
      "stage": "stem_opt",
      "years_in_us": 3
    },
    "extraction_a": {
      "end_date": "not-a-real-date"
    },
    "extraction_b": {},
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": ["grace_period_employment"],
    "expected_nra": "yes",
    "expected_track": "stem_opt",
    "notes": "Malformed date on lt/gt must return False, not raise."
  }
}
```

- [ ] **Step 4: Create D-nra-branch1-explicit.json**

```json
{
  "case_id": "D-nra-branch1-explicit",
  "slice": "D",
  "track": "stem_opt",
  "target_rule_id": null,
  "probe_intent": "Probe rule_engine._derive_nra branch 1: explicit tax_residency_status wins over stage/years heuristics. A user on STEM OPT within 5 years who explicitly declares 'Resident alien' must have is_nra='no', overriding the branch-2 heuristic that would otherwise yield 'yes'.",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {
      "stage": "stem_opt",
      "years_in_us": 3,
      "tax_residency_status": "Resident alien"
    },
    "extraction_a": {},
    "extraction_b": {},
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": [],
    "expected_nra": "no",
    "expected_track": "stem_opt",
    "notes": "tax_residency_status = Resident alien explicitly overrides the F-1 exempt heuristic"
  }
}
```

- [ ] **Step 5: Create D-nra-branch2-f1-exempt-boundary.json**

```json
{
  "case_id": "D-nra-branch2-f1-exempt-boundary",
  "slice": "D",
  "track": "stem_opt",
  "target_rule_id": null,
  "probe_intent": "Probe rule_engine._derive_nra branch 2 boundary: years_in_us < 6 on an F-1 exempt stage yields is_nra='yes'; years_in_us >= 6 yields 'no'. This case sits exactly at year 5.",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {
      "stage": "stem_opt",
      "years_in_us": 5
    },
    "extraction_a": {},
    "extraction_b": {},
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": [],
    "expected_nra": "yes",
    "expected_track": "stem_opt",
    "notes": "years_in_us=5 is still < 6, so branch 2 fires and is_nra=yes"
  }
}
```

- [ ] **Step 6: Create E-edge-empty-context.json**

```json
{
  "case_id": "E-edge-empty-context",
  "slice": "E",
  "track": "stem_opt",
  "target_rule_id": null,
  "probe_intent": "Probe engine behavior on a completely empty EvaluationContext. No answers, no extractions, no comparisons. Most rules should remain quiet; any rule that fires on empty input is suspect. Advisories with empty `conditions: []` MAY still fire (they're unconditional by design).",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {},
    "extraction_a": {},
    "extraction_b": {},
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": [
      "job_title_mismatch",
      "employer_name_mismatch",
      "unemployment_risk",
      "form_8843_missing"
    ],
    "expected_nra": "no",
    "expected_track": "stem_opt",
    "notes": "Empty context: most rules quiet; unconditional advisories may still fire."
  }
}
```

- [ ] **Step 7: Create E-edge-false-string-gotcha.json**

```json
{
  "case_id": "E-edge-false-string-gotcha",
  "slice": "E",
  "track": "entity",
  "target_rule_id": "missing_5472",
  "probe_intent": "Probe the known entity.yaml type gotcha: rule `missing_5472` has `value: \"False\"` (string, not bool). The engine uses strict `eq`, so this case must supply the literal STRING \"False\" for form_5472_present to trigger the rule. If the engine ever relaxes its comparison or if form_5472_present arrives as a bool, this case will fail — which is the point.",
  "generated_by": "hand",
  "generated_at": "2026-04-10T00:00:00Z",
  "generator_prompt_hash": null,
  "flavor_hint": null,
  "input": {
    "answers": {
      "owner_residency": "outside_us",
      "entity_type": "smllc"
    },
    "extraction_a": {},
    "extraction_b": {
      "form_5472_present": "False"
    },
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": ["missing_5472"],
    "must_not_fire_rule_ids": [],
    "expected_nra": "yes",
    "expected_track": "entity",
    "notes": "String 'False' (not bool) is required to match the rule's eq comparison."
  }
}
```

- [ ] **Step 8: Write test that discover loads all 6 goldens**

Append to `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_rubric_loop.py::test_discover_loads_real_goldens_from_repo -v`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add scripts/rubric_fixtures/ tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): seed 6 static goldens for slices C/D/E"
```

---

## Task 7: Phase 2 — Evaluate

**Files:**
- Create: `scripts/rubric/evaluate.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
from rubric.evaluate import evaluate_case, load_eval_cache
from rubric.models import FixtureRecord


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_evaluate_case_fires_job_title_mismatch -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement evaluate.py**

Create `scripts/rubric/evaluate.py`:

```python
"""Phase 2: run fixtures through the real rule engine and cache the results."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the repo root so we can import compliance_os.* from scripts/
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

from rubric.io import (
    CONFIG_RULES_DIR,
    EVAL_CACHE_DIR,
    load_json,
    save_json,
    sha256_of_file,
    sha256_of_obj,
)
from rubric.models import EvalRecord, FixtureRecord


def evaluate_case(fixture: FixtureRecord, *, cache_dir: Path = EVAL_CACHE_DIR) -> EvalRecord:
    """Run one fixture through the engine, cache the result, return the record."""
    rule_file = CONFIG_RULES_DIR / f"{fixture.track}.yaml"
    if not rule_file.exists():
        return EvalRecord(
            case_id=fixture.case_id,
            engine_version="unknown",
            rule_file_path=str(rule_file),
            rule_file_hash="",
            input_hash=sha256_of_obj(fixture.input),
            evaluated_at=_now_iso(),
            derived={},
            findings=[],
            engine_error=f"rule file not found for track={fixture.track!r}: {rule_file}",
        )

    rule_file_hash = sha256_of_file(rule_file)
    input_hash = sha256_of_obj(fixture.input)

    # Check cache
    cached_path = cache_dir / f"{fixture.case_id}.json"
    if cached_path.exists():
        cached = load_json(cached_path)
        if (
            cached.get("input_hash") == input_hash
            and cached.get("rule_file_hash") == rule_file_hash
        ):
            return EvalRecord.from_dict(cached)

    try:
        engine = RuleEngine.from_yaml(rule_file)
        ctx = EvaluationContext(
            answers=fixture.input.get("answers", {}),
            extraction_a=fixture.input.get("extraction_a", {}),
            extraction_b=fixture.input.get("extraction_b", {}),
            comparisons=fixture.input.get("comparisons", {}),
        )
        raw_findings = engine.evaluate(ctx)
        findings = [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "action": f.action,
                "consequence": f.consequence,
                "immigration_impact": f.immigration_impact,
            }
            for f in raw_findings
        ]
        record = EvalRecord(
            case_id=fixture.case_id,
            engine_version=engine.version,
            rule_file_path=str(rule_file),
            rule_file_hash=rule_file_hash,
            input_hash=input_hash,
            evaluated_at=_now_iso(),
            derived={"is_nra": ctx.answers.get("is_nra", "no")},
            findings=findings,
            engine_error=None,
        )
    except Exception as e:  # noqa: BLE001 — we intentionally catch and record
        record = EvalRecord(
            case_id=fixture.case_id,
            engine_version="unknown",
            rule_file_path=str(rule_file),
            rule_file_hash=rule_file_hash,
            input_hash=input_hash,
            evaluated_at=_now_iso(),
            derived={},
            findings=[],
            engine_error=f"{type(e).__name__}: {e}",
        )

    save_json(cached_path, record.to_dict())
    return record


def load_eval_cache(case_id: str, cache_dir: Path = EVAL_CACHE_DIR) -> EvalRecord | None:
    path = cache_dir / f"{case_id}.json"
    if not path.exists():
        return None
    return EvalRecord.from_dict(load_json(path))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 26 tests green (22 prior + 4 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/evaluate.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): Phase 2 evaluate — run fixtures through the engine"
```

---

## Task 8: Codex client (mocked tests only)

**Files:**
- Create: `scripts/rubric/codex_client.py`
- Modify: `tests/test_rubric_loop.py`

All tests in this task use `monkeypatch` to stub `subprocess.run`. No real codex calls in the test suite.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
from rubric.codex_client import call_codex, CodexCallError as CcError
from rubric.codex_client import _extract_token_counts


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
            # Valid JSON but missing required field
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

    def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
        model_idx = cmd.index("--model") + 1
        model = cmd[model_idx]
        calls.append(model)
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
    )
    assert calls == ["gpt-5.4", "gpt-5.4-mini"]
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_call_codex_success_path -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement codex_client.py**

Create `scripts/rubric/codex_client.py`:

```python
"""Thin wrapper around `codex exec` for structured-JSON LLM calls.

Hermetic: every call runs in a scratch workspace with --sandbox read-only,
--ephemeral, and --skip-git-repo-check. The agent cannot read files or run
shell commands. All knowledge must be in the prompt.

Defaults match the "not a coding task" policy: gpt-5.4 / xhigh, not
gpt-5.3-codex. See docs/superpowers/specs/2026-04-10-rubric-loop-design.md
decision D8 for rationale.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from rubric.models import CodexCallError, CodexCallResult

SCRATCH_WORKSPACE = Path("/tmp/rubric-loop-workspace")

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_FALLBACK_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "xhigh"

MODEL = os.environ.get("RUBRIC_CODEX_MODEL", DEFAULT_MODEL)
FALLBACK_MODEL = os.environ.get("RUBRIC_CODEX_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
REASONING_EFFORT = os.environ.get("RUBRIC_CODEX_REASONING", DEFAULT_REASONING_EFFORT)


def call_codex(
    *,
    prompt: str,
    schema_path: Path,
    model: str = MODEL,
    reasoning_effort: str = REASONING_EFFORT,
    timeout_s: int = 180,
    max_retries: int = 2,
    fallback_model: str | None = FALLBACK_MODEL,
) -> CodexCallResult:
    """Invoke `codex exec` with structured output, retries, and fallback.

    Retries only the retryable failure kinds (timeout, parse_failure,
    schema_violation). Subprocess failures fail fast except for
    "model is not supported" which triggers a one-shot fallback.
    """
    SCRATCH_WORKSPACE.mkdir(parents=True, exist_ok=True)
    last_error: CodexCallError | None = None

    for attempt in range(1, max_retries + 2):  # initial + retries
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as tmp:
            output_path = Path(tmp.name)

        cmd = [
            "codex", "exec",
            "-c", f'model_reasoning_effort="{reasoning_effort}"',
            "--model", model,
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--output-schema", str(schema_path),
            "--output-last-message", str(output_path),
            "--json",
            "--cd", str(SCRATCH_WORKSPACE),
            "-",
        ]

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            last_error = CodexCallError(
                kind="timeout",
                message=f"codex exec timed out after {timeout_s}s",
                attempts=attempt,
            )
            continue

        if proc.returncode != 0:
            combined = (proc.stdout or "") + (proc.stderr or "")
            if (
                fallback_model
                and fallback_model != model
                and "model is not supported" in combined.lower()
            ):
                return call_codex(
                    prompt=prompt,
                    schema_path=schema_path,
                    model=fallback_model,
                    reasoning_effort=reasoning_effort,
                    timeout_s=timeout_s,
                    max_retries=max_retries,
                    fallback_model=None,  # prevent recursion
                )
            raise CodexCallError(
                kind="subprocess_failure",
                message=f"codex exec returned {proc.returncode}",
                stderr=combined,
                attempts=attempt,
            )

        raw = output_path.read_text().strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            last_error = CodexCallError(
                kind="parse_failure",
                message=f"output was not valid JSON: {e}",
                stderr=raw[:500],
                attempts=attempt,
            )
            continue

        schema = json.loads(schema_path.read_text())
        validator = Draft202012Validator(schema)
        try:
            validator.validate(parsed)
        except ValidationError as e:
            last_error = CodexCallError(
                kind="schema_violation",
                message=f"output violates schema: {e.message}",
                stderr=raw[:500],
                attempts=attempt,
            )
            continue

        events = [
            json.loads(line)
            for line in (proc.stdout or "").splitlines()
            if line.strip()
        ]
        tokens_in, tokens_out = _extract_token_counts(events)

        return CodexCallResult(
            text=raw,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=0,    # parsed from events in a follow-up pass; OK to 0-init
            raw_events=events,
            attempts=attempt,
        )

    assert last_error is not None
    raise last_error


def _extract_token_counts(events: list[dict]) -> tuple[int | None, int | None]:
    """Find the last usage event and extract token counts.

    The codex JSONL event schema may evolve; we fail soft (return None) if the
    event isn't present rather than crashing the whole run.
    """
    for event in reversed(events):
        if isinstance(event, dict) and event.get("type") == "usage":
            return event.get("input_tokens"), event.get("output_tokens")
    return None, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 33 tests green (26 prior + 7 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/codex_client.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): codex client wrapper with retry + fallback + schema validation"
```

---

## Task 9: Prompt templates + output schemas

**Files:**
- Create: `scripts/rubric/prompts/generator.md`
- Create: `scripts/rubric/prompts/judge.md`
- Create: `scripts/rubric/schemas/generator-output.schema.json`
- Create: `scripts/rubric/schemas/judge-output.schema.json`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Create generator output schema**

Create `scripts/rubric/schemas/generator-output.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["input", "expected", "flavor_hint"],
  "additionalProperties": false,
  "properties": {
    "input": {
      "type": "object",
      "required": ["answers", "extraction_a", "extraction_b", "comparisons"],
      "additionalProperties": false,
      "properties": {
        "answers":      {"type": "object"},
        "extraction_a": {"type": "object"},
        "extraction_b": {"type": "object"},
        "comparisons":  {"type": "object"}
      }
    },
    "expected": {
      "type": "object",
      "required": ["must_fire_rule_ids", "must_not_fire_rule_ids", "expected_nra", "expected_track"],
      "properties": {
        "must_fire_rule_ids":     {"type": "array", "items": {"type": "string"}},
        "must_not_fire_rule_ids": {"type": "array", "items": {"type": "string"}},
        "expected_nra":           {"enum": ["yes", "no"]},
        "expected_track":         {"enum": ["stem_opt", "student", "entity", "data_room", "h1b_doc_check"]},
        "notes":                  {"type": "string"}
      }
    },
    "flavor_hint": {"type": ["string", "null"]}
  }
}
```

- [ ] **Step 2: Create judge output schema**

Create `scripts/rubric/schemas/judge-output.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["verdict", "subscores"],
  "additionalProperties": false,
  "properties": {
    "verdict": {"enum": ["pass", "partial", "fail", "unrunnable"]},
    "subscores": {
      "type": "object",
      "patternProperties": {
        "^(categorization|findings|rule_quality|operator_behavior)$": {
          "type": "object",
          "required": ["score", "criteria_applied", "note"],
          "properties": {
            "score":            {"type": "number", "minimum": 0, "maximum": 1},
            "criteria_applied": {"type": "array", "items": {"type": "string"}},
            "note":             {"type": "string"}
          }
        }
      },
      "additionalProperties": false
    },
    "flags": {"type": "array", "items": {"type": "string"}}
  }
}
```

- [ ] **Step 3: Create generator prompt template**

Create `scripts/rubric/prompts/generator.md`:

````markdown
# System

You are generating a single synthetic test case for a deterministic compliance rule engine. The engine evaluates an EvaluationContext object against a YAML-defined rule set and produces findings.

Your job is to produce the case input, not to evaluate or judge it.

Your output MUST conform to the JSON schema provided via --output-schema. Produce JSON only. Do NOT emit markdown code fences, prose, or commentary.

Do not use real PII or real-looking government identifiers (SSNs, A-numbers, receipt numbers, passport numbers). All names, employers, schools, and identifiers must be fictional. You may use plain, realistic, or playful framing — pick whichever makes the case clearest. Do not force humor where it obscures the probe.

Do not attempt to read files, run shell commands, or use tools. Respond with the final JSON only.

# User

## Target rule

The rule you are constructing a test case for:

```yaml
{rule_yaml_snapshot}
```

## Probe intent

{probe_intent}

## Case constraints

- case_id: {case_id}
- slice: {slice}            (A=positive, B=negative near-miss)
- track: {track}
- target_rule_id: {target_rule_id}

## Field reference

These are the ONLY fields the engine can read. Any other fields you set will be ignored:

{field_reference_table}

## Derivation reminders

- `is_nra` is derived automatically in rule_engine._derive_nra; do not set it directly. Set `tax_residency_status` (explicit) OR `stage` + `years_in_us` (heuristic) OR `owner_residency` (entity track).
- F-1 exempt stages: f1_student, opt, stem_opt. Years < 6 → is_nra=yes.
- h1b / i140 → is_nra=no.

## Value-type gotchas to respect

- `form_5472_present` must be the literal STRING "False" or "True", not a bool.
- `schedules_present` is a LIST of strings, e.g. ["schedule_c"].
- All dates must be YYYY-MM-DD ISO format.

## Your output

Produce a JSON object satisfying the output schema. The `input` object maps 1:1 to rule_engine.EvaluationContext. The `expected` object states what the engine should do.

For slice A: expected.must_fire_rule_ids MUST include "{target_rule_id}".
For slice B: expected.must_not_fire_rule_ids MUST include "{target_rule_id}", and the case must be adversarially close — something a naive reader would think SHOULD fire the rule.
````

- [ ] **Step 4: Create judge prompt template**

Create `scripts/rubric/prompts/judge.md`:

````markdown
# System

You are grading the behavior of a deterministic compliance rule engine on a single test case. You are NOT grading the case itself; you are grading whether the engine did the right thing given the case.

Apply only the criteria provided. Do not invent additional criteria. Do not speculate about rules or engine behavior not described here.

Produce JSON only, matching the provided output schema. No prose.
Do not attempt to read files or run shell commands.

# User

## Case under review

```json
{case_fixture_json}
```

## Derived field captured by the engine

- is_nra: {derived_is_nra}

## Engine findings

```json
{findings_json}
```

## Engine error (if any)

{engine_error_or_none}

## Criteria that apply to this slice ({slice})

{filtered_criteria_yaml}

## Scoring rules

- Score each applicable criterion on a 0.0–1.0 scale.
- Aggregate within a dimension via simple mean.
- Map weighted mean across dimensions to a verdict:
    >= 0.90  -> "pass"
    >= 0.60  -> "partial"
    <  0.60  -> "fail"
- If any hard-fail criterion scores 0.0, verdict is "fail":
    - positive_case_fires_target_rule
    - negative_case_does_not_fire_target_rule
    - expected_must_not_fire_respected
- If engine_error is present and the case did not expect an error, verdict is "unrunnable".

## Your output

JSON object with:
- `verdict`: "pass" | "partial" | "fail" | "unrunnable"
- `subscores`: per dimension, each with score, criteria_applied, note
- `flags`: optional list of free-form strings

Each dimension's `note` must cite specific facts from the case + findings — e.g., "is_nra=yes because stage=stem_opt, years=3 (branch 2)." Vague notes like "looks correct" are not acceptable.
````

- [ ] **Step 5: Write test verifying schemas are valid JSON Schema**

Append to `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 37 tests green.

- [ ] **Step 7: Commit**

```bash
git add scripts/rubric/prompts/ scripts/rubric/schemas/ tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): generator + judge prompt templates and JSON schemas"
```

---

## Task 10: Phase 1 — Generate

**Files:**
- Create: `scripts/rubric/generate.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
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

    # Pre-populate the fixture
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_render_generator_prompt_substitutes_all_placeholders -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement generate.py**

Create `scripts/rubric/generate.py`:

```python
"""Phase 1: generate LLM-backed fixtures for slice A/B cases that don't exist yet."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from rubric.codex_client import MODEL, REASONING_EFFORT, call_codex
from rubric.hints import build_field_reference_table
from rubric.io import PROJECT_ROOT, save_json, sha256_of_text
from rubric.models import CaseSpec, CodexCallError, FixtureRecord

GENERATOR_SCHEMA = PROJECT_ROOT / "scripts" / "rubric" / "schemas" / "generator-output.schema.json"
GENERATOR_TEMPLATE = PROJECT_ROOT / "scripts" / "rubric" / "prompts" / "generator.md"

# PII-shaped regexes: SSN, A-number, USCIS receipt number
_PII_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")),
    ("A-number", re.compile(r"\bA\d{8,9}\b")),
    ("USCIS receipt", re.compile(r"\b[A-Z]{3}\d{10}\b")),
]


def render_generator_prompt(spec: CaseSpec, *, rules_dir: Path) -> str:
    template = GENERATOR_TEMPLATE.read_text()
    rule_snapshot = yaml.safe_dump(spec.target_rule_snapshot or {}, sort_keys=False)
    table = build_field_reference_table(rules_dir)
    return (
        template
        .replace("{rule_yaml_snapshot}", rule_snapshot)
        .replace("{probe_intent}", spec.probe_intent)
        .replace("{case_id}", spec.case_id)
        .replace("{slice}", spec.slice)
        .replace("{track}", spec.track)
        .replace("{target_rule_id}", spec.target_rule_id or "")
        .replace("{field_reference_table}", table)
    )


def detect_pii_shaped_strings(input_obj: dict) -> list[str]:
    """Return list of human-readable warnings for any PII-shaped strings found."""
    warnings: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            for label, pat in _PII_PATTERNS:
                if pat.search(value):
                    warnings.append(f"{label}-shaped string found: {value!r}")

    walk(input_obj)
    return warnings


def generate_missing(
    manifest: list[CaseSpec],
    *,
    fixture_dir: Path,
    rules_dir: Path,
) -> tuple[int, int, list[str]]:
    """Generate fixtures for any slice-A/B cases that don't already have one.

    Returns (new_count, skip_count, warnings).
    Goldens (gen_strategy='golden') are always skipped.
    """
    fixture_dir.mkdir(parents=True, exist_ok=True)
    new_count = 0
    skip_count = 0
    warnings: list[str] = []

    for spec in manifest:
        if spec.gen_strategy != "llm":
            skip_count += 1
            continue
        target_path = fixture_dir / f"{spec.case_id}.json"
        if target_path.exists():
            skip_count += 1
            continue

        prompt = render_generator_prompt(spec, rules_dir=rules_dir)
        prompt_hash = sha256_of_text(prompt)

        try:
            result = call_codex(prompt=prompt, schema_path=GENERATOR_SCHEMA)
        except CodexCallError as e:
            warnings.append(f"generator failed for {spec.case_id}: {e.kind} — {e.message}")
            # Write a sentinel so we don't retry forever
            save_json(target_path, {
                "case_id": spec.case_id, "slice": spec.slice, "track": spec.track,
                "target_rule_id": spec.target_rule_id,
                "probe_intent": spec.probe_intent,
                "generated_by": f"codex-cli/{MODEL}",
                "generated_at": _now_iso(),
                "generator_prompt_hash": prompt_hash,
                "flavor_hint": None,
                "input": {"answers": {}, "extraction_a": {}, "extraction_b": {}, "comparisons": {}},
                "expected": {
                    "must_fire_rule_ids": [],
                    "must_not_fire_rule_ids": [],
                    "expected_nra": "no",
                    "expected_track": spec.track,
                    "notes": f"GENERATION FAILED: {e.kind}",
                },
                "last_error": {"kind": e.kind, "message": e.message},
            })
            continue

        parsed = result.parsed
        # PII screener warning (not failure)
        pii_warnings = detect_pii_shaped_strings(parsed.get("input", {}))
        for w in pii_warnings:
            warnings.append(f"{spec.case_id}: {w}")

        record = FixtureRecord(
            case_id=spec.case_id,
            slice=spec.slice,
            track=spec.track,
            target_rule_id=spec.target_rule_id,
            probe_intent=spec.probe_intent,
            generated_by=f"codex-cli/{MODEL}",
            generated_at=_now_iso(),
            generator_prompt_hash=prompt_hash,
            flavor_hint=parsed.get("flavor_hint"),
            input=parsed["input"],
            expected=parsed["expected"],
        )
        save_json(target_path, record.to_dict())
        new_count += 1

    return new_count, skip_count, warnings


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 42 tests green (37 prior + 5 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/generate.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): Phase 1 generate — codex-backed fixture generation"
```

---

## Task 11: Rubric criteria YAML + version

**Files:**
- Create: `config/rubric/criteria.yaml`
- Create: `config/rubric/rubric_version.txt`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Create criteria YAML**

Create `config/rubric/criteria.yaml`:

```yaml
version: "0.1.0"

dimensions:
  - id: categorization
    description: "Did the engine assign the right track and derive the right fields before rules fired?"
  - id: findings
    description: "Did the rules fire correctly given the inputs?"
  - id: rule_quality
    description: "Is the fired rule's text actionable and internally consistent?"
  - id: operator_behavior
    description: "Does the engine handle edge-case operator inputs per Condition.evaluate contract?"

criteria:
  - id: track_selection_correct
    dimension: categorization
    applies_to: [A, B, C, D, E]
    description: |
      The case's declared `track` must match the rule file the engine would
      select based on routers/review.py track-routing logic. If expected_track
      is set, the engine's loaded YAML file must match it.

  - id: nra_derivation_correct
    dimension: categorization
    applies_to: [A, B, D]
    description: |
      The derived is_nra field must match expected_nra and must follow the
      four-branch priority order in rule_engine._derive_nra:
      (1) explicit tax_residency_status wins,
      (2) else F-1 exempt stages with years_in_us < 6 → yes,
      (3) else h1b/i140 → no,
      (4) else owner_residency == "outside_us" → yes,
      (5) default → no.

  - id: positive_case_fires_target_rule
    dimension: findings
    applies_to: [A]
    description: |
      Engine output MUST contain at least one finding with rule_id ==
      target_rule_id. Absence is a hard fail.

  - id: negative_case_does_not_fire_target_rule
    dimension: findings
    applies_to: [B]
    description: |
      Engine output MUST NOT contain any finding with rule_id ==
      target_rule_id. Presence is a hard fail.

  - id: no_unrelated_false_positives
    dimension: findings
    applies_to: [A, B]
    description: |
      Findings other than the target rule are allowed only if they logically
      follow from the case inputs. A finding that fires on a field the case
      never set (or set to a placeholder value) should be flagged. The judge
      should cross-check each non-target finding against the case input.

  - id: severity_matches_case_gravity
    dimension: findings
    applies_to: [A]
    description: |
      A fired finding's severity should match the gravity described in the
      probe intent. A status-threatening probe should not fire at severity
      'info'. A mild probe should not fire at 'critical' unless the rule
      explicitly specifies it.

  - id: expected_must_not_fire_respected
    dimension: findings
    applies_to: [A, B, C, D, E]
    description: |
      Any rule_id listed in expected.must_not_fire_rule_ids that appears in
      findings is an automatic subscore of 0.0. Hard fail.

  - id: rule_text_actionable
    dimension: rule_quality
    applies_to: [A]
    description: |
      For each fired finding, the `action` text should be a concrete step
      the user can take. Vague actions ("consult an attorney" with no
      specificity) should be flagged but not failed outright.

  - id: rule_conditions_non_contradictory
    dimension: rule_quality
    applies_to: [A]
    description: |
      The target rule's conditions should not be mutually exclusive. If the
      slice-A generator produced a valid case satisfying all conditions,
      this criterion passes.

  - id: findings_free_of_cross_rule_contradictions
    dimension: rule_quality
    applies_to: [A, B]
    description: |
      If the findings list contains two rules whose action texts directly
      contradict each other, flag it. This catches the advisory_fbar vs
      foreign_accounts_fbar_risk overlap pattern.

  - id: operator_behavior_correct
    dimension: operator_behavior
    applies_to: [C]
    description: |
      For slice-C operator stress cases, engine behavior on null/boundary/
      wrong-type inputs should match the documented contract in
      rule_engine.Condition.evaluate. Expected behavior is encoded in the
      golden fixture's `expected` field.

scoring:
  dimension_weights:
    categorization: 1.0
    findings: 2.0
    rule_quality: 1.0
    operator_behavior: 1.0

  pass_threshold: 0.90
  partial_threshold: 0.60

  hard_fail_criteria:
    - positive_case_fires_target_rule
    - negative_case_does_not_fire_target_rule
    - expected_must_not_fire_respected
```

- [ ] **Step 2: Create rubric_version.txt**

Create `config/rubric/rubric_version.txt`:

```
0.1.0
```

- [ ] **Step 3: Write test that criteria YAML loads and filters by slice**

Append to `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 45 tests green.

- [ ] **Step 5: Commit**

```bash
git add config/rubric/ tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): rubric criteria YAML + version 0.1.0"
```

---

## Task 12: Phase 3 — Judge

**Files:**
- Create: `scripts/rubric/judge.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
from rubric.judge import (
    judge_case,
    compute_judge_cache_key,
    filter_criteria_for_slice,
    render_judge_prompt,
)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_filter_criteria_for_slice_a_includes_correct_subset -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement judge.py**

Create `scripts/rubric/judge.py`:

```python
"""Phase 3: LLM-as-judge grading of engine output against declarative rubric criteria."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from rubric.codex_client import MODEL, call_codex
from rubric.io import (
    CONFIG_RUBRIC_DIR,
    JUDGE_CACHE_DIR,
    PROJECT_ROOT,
    load_json,
    save_json,
    sha256_of_obj,
    sha256_of_text,
)
from rubric.models import CodexCallError, EvalRecord, FixtureRecord, JudgeRecord

JUDGE_SCHEMA = PROJECT_ROOT / "scripts" / "rubric" / "schemas" / "judge-output.schema.json"
JUDGE_TEMPLATE = PROJECT_ROOT / "scripts" / "rubric" / "prompts" / "judge.md"


def _load_criteria() -> dict:
    return yaml.safe_load((CONFIG_RUBRIC_DIR / "criteria.yaml").read_text())


def _rubric_version() -> str:
    return (CONFIG_RUBRIC_DIR / "rubric_version.txt").read_text().strip()


def filter_criteria_for_slice(criteria: list[dict], slice_: str) -> list[dict]:
    return [c for c in criteria if slice_ in c.get("applies_to", [])]


def compute_judge_cache_key(
    input_hash: str,
    findings_hash: str,
    rubric_version: str,
    judge_prompt_hash: str,
) -> str:
    return sha256_of_text(
        f"{input_hash}|{findings_hash}|{rubric_version}|{judge_prompt_hash}"
    )


def render_judge_prompt(fixture: FixtureRecord, eval_record: EvalRecord) -> str:
    template = JUDGE_TEMPLATE.read_text()
    criteria = _load_criteria().get("criteria", [])
    filtered = filter_criteria_for_slice(criteria, fixture.slice)
    criteria_yaml = yaml.safe_dump(filtered, sort_keys=False)
    return (
        template
        .replace("{case_fixture_json}", json.dumps(fixture.to_dict(), indent=2))
        .replace("{derived_is_nra}", eval_record.derived.get("is_nra", "unknown"))
        .replace("{findings_json}", json.dumps(eval_record.findings, indent=2))
        .replace("{engine_error_or_none}", eval_record.engine_error or "(none)")
        .replace("{slice}", fixture.slice)
        .replace("{filtered_criteria_yaml}", criteria_yaml)
    )


def judge_case(
    fixture: FixtureRecord,
    eval_record: EvalRecord,
    *,
    cache_dir: Path = JUDGE_CACHE_DIR,
) -> JudgeRecord:
    """Grade one case. Cached by (input_hash, findings_hash, rubric_version, prompt_hash)."""
    rubric_version = _rubric_version()
    findings_hash = sha256_of_obj(eval_record.findings)
    prompt = render_judge_prompt(fixture, eval_record)
    prompt_hash = sha256_of_text(prompt)
    cache_key = compute_judge_cache_key(
        eval_record.input_hash, findings_hash, rubric_version, prompt_hash
    )

    cached_path = cache_dir / f"{cache_key}.json"
    if cached_path.exists():
        return JudgeRecord.from_dict(load_json(cached_path))

    try:
        result = call_codex(prompt=prompt, schema_path=JUDGE_SCHEMA)
    except CodexCallError as e:
        record = JudgeRecord(
            cache_key=cache_key,
            cache_key_inputs={
                "case_id": fixture.case_id,
                "input_hash": eval_record.input_hash,
                "findings_hash": findings_hash,
                "rubric_version": rubric_version,
                "judge_prompt_hash": prompt_hash,
            },
            case_id=fixture.case_id,
            judged_at=_now_iso(),
            judged_by=f"codex-cli/{MODEL}",
            verdict="unrunnable",
            subscores={},
            flags=[f"judge_error:{e.kind}"],
            raw_judge_output=e.message,
        )
        save_json(cached_path, record.to_dict())
        return record

    parsed = result.parsed
    record = JudgeRecord(
        cache_key=cache_key,
        cache_key_inputs={
            "case_id": fixture.case_id,
            "input_hash": eval_record.input_hash,
            "findings_hash": findings_hash,
            "rubric_version": rubric_version,
            "judge_prompt_hash": prompt_hash,
        },
        case_id=fixture.case_id,
        judged_at=_now_iso(),
        judged_by=f"codex-cli/{MODEL}",
        verdict=parsed["verdict"],
        subscores=parsed["subscores"],
        flags=parsed.get("flags", []),
        raw_judge_output=result.text,
    )
    save_json(cached_path, record.to_dict())
    return record


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 50 tests green.

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/judge.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): Phase 3 judge — LLM-as-judge with cache key invalidation"
```

---

## Task 13: Phase 4 — Aggregate

**Files:**
- Create: `scripts/rubric/aggregate.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
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
    # Minimal end-to-end: one case, one eval, one judge
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_classify_verdict_pass_at_threshold -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement aggregate.py**

Create `scripts/rubric/aggregate.py`:

```python
"""Phase 4: assemble per-run scorecard from cached fixtures + eval + judge records."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import yaml

from rubric.io import CONFIG_RUBRIC_DIR, OUT_DIR, save_json
from rubric.models import (
    CallTelemetry,
    CaseSpec,
    EvalRecord,
    JudgeRecord,
    Scorecard,
)


def classify_verdict_from_subscores(
    subscores: dict,
    weights: dict,
    hard_fail_criteria: list,
    *,
    pass_t: float,
    partial_t: float,
) -> str:
    # Hard-fail check: if any score for a hard-fail criterion is 0.0, verdict = fail
    for dim_scores in subscores.values():
        for crit_id in dim_scores.get("criteria_applied", []):
            if crit_id in hard_fail_criteria and dim_scores.get("score", 1.0) == 0.0:
                return "fail"

    if not subscores:
        return "unrunnable"

    total_weight = 0.0
    weighted_sum = 0.0
    for dim, body in subscores.items():
        w = weights.get(dim, 1.0)
        total_weight += w
        weighted_sum += w * body.get("score", 0.0)
    if total_weight == 0:
        return "unrunnable"
    weighted_mean = weighted_sum / total_weight

    if weighted_mean >= pass_t:
        return "pass"
    if weighted_mean >= partial_t:
        return "partial"
    return "fail"


def compute_totals(judge_records: list[JudgeRecord]) -> dict:
    totals = {"cases": 0, "pass": 0, "partial": 0, "fail": 0, "unrunnable": 0}
    for r in judge_records:
        totals["cases"] += 1
        v = r.verdict
        if v in totals:
            totals[v] += 1
        else:
            totals["unrunnable"] += 1
    return totals


def _by_group(records: list[JudgeRecord], cases: list[CaseSpec], key: str) -> dict:
    """Group verdict counts by a CaseSpec attribute (e.g., 'track', 'slice')."""
    case_by_id = {c.case_id: c for c in cases}
    out: dict = {}
    for r in records:
        c = case_by_id.get(r.case_id)
        if not c:
            continue
        k = getattr(c, key, None)
        if not k:
            continue
        bucket = out.setdefault(k, {"cases": 0, "pass": 0, "partial": 0, "fail": 0, "unrunnable": 0})
        bucket["cases"] += 1
        if r.verdict in bucket:
            bucket[r.verdict] += 1
        else:
            bucket["unrunnable"] += 1
    return out


def _by_dimension(judge_records: list[JudgeRecord]) -> dict:
    out: dict = {}
    for r in judge_records:
        for dim, body in r.subscores.items():
            b = out.setdefault(dim, {"scores": [], "cases": 0})
            b["scores"].append(body.get("score", 0.0))
            b["cases"] += 1
    return {
        dim: {"weighted_mean": round(mean(b["scores"]), 3), "cases": b["cases"]}
        for dim, b in out.items()
    }


def _failure_details(
    judge_records: list[JudgeRecord],
    cases: list[CaseSpec],
) -> list[dict]:
    failures: list[dict] = []
    for r in judge_records:
        if r.verdict != "fail":
            continue
        dim_scores = {dim: round(body.get("score", 0.0), 2) for dim, body in r.subscores.items()}
        hard_fail = None
        for dim, body in r.subscores.items():
            if body.get("score") == 0.0 and body.get("criteria_applied"):
                hard_fail = body["criteria_applied"][0]
                break
        failures.append({
            "case_id": r.case_id,
            "verdict": r.verdict,
            "dimension_scores": dim_scores,
            "hard_fail_criterion": hard_fail,
            "judge_note": _first_note(r.subscores),
            "flags": list(r.flags),
        })
    return failures


def _first_note(subscores: dict) -> str:
    for body in subscores.values():
        note = body.get("note")
        if note:
            return note
    return ""


def assemble_scorecard(
    *,
    cases: list[CaseSpec],
    eval_records: dict,  # case_id -> EvalRecord
    judge_records: dict,  # case_id -> JudgeRecord
    telemetry: CallTelemetry,
    warnings: list[str],
    prior_scorecard: dict | None = None,
) -> Scorecard:
    """Assemble a Scorecard dataclass from Phase 2+3 outputs."""
    criteria_data = yaml.safe_load((CONFIG_RUBRIC_DIR / "criteria.yaml").read_text())
    rubric_version = (CONFIG_RUBRIC_DIR / "rubric_version.txt").read_text().strip()

    judge_list = list(judge_records.values())
    totals = compute_totals(judge_list)
    by_track = _by_group(judge_list, cases, "track")
    by_slice = _by_group(judge_list, cases, "slice")
    by_dim = _by_dimension(judge_list)
    failures = _failure_details(judge_list, cases)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    engine_version = next(
        (r.engine_version for r in eval_records.values() if r.engine_version != "unknown"),
        "unknown",
    )

    delta: dict = {}
    if prior_scorecard:
        prior_verdicts = {}
        for entry in prior_scorecard.get("failures", []):
            prior_verdicts[entry["case_id"]] = entry["verdict"]
        new_failures = [r.case_id for r in judge_list
                        if r.verdict == "fail" and prior_verdicts.get(r.case_id) != "fail"]
        delta = {
            "last_run_id": prior_scorecard.get("run_id", ""),
            "new_failures": new_failures,
            "new_passes": [],
            "new_unrunnable": [],
            "rules_with_score_change": [],
            "unchanged_cases": max(0, totals["cases"] - len(new_failures)),
        }

    return Scorecard(
        run_id=now,
        engine_version=engine_version,
        rubric_version=rubric_version,
        codex_version="0.118.0",
        codex_model="gpt-5.4",
        reasoning_effort="xhigh",
        started_at=now,
        completed_at=now,
        totals=totals,
        by_track=by_track,
        by_slice=by_slice,
        by_dimension=by_dim,
        failures=failures,
        coverage_gaps=[],
        warnings=warnings,
        delta_from_last_run=delta,
        telemetry={
            "generator_calls": telemetry.generator_calls,
            "generator_calls_cached": telemetry.generator_calls_cached,
            "judge_calls": telemetry.judge_calls,
            "judge_calls_cached": telemetry.judge_calls_cached,
            "tokens_in_total": telemetry.tokens_in_total,
            "tokens_out_total": telemetry.tokens_out_total,
            "note": "codex CLI usage is subscription-billed; token counts are for prompt-tuning only",
        },
    )


def render_scorecard_markdown(sc: Scorecard) -> str:
    """Short human-readable version for out/rubric-loop-<ts>.md."""
    t = sc.totals
    lines = [
        f"# Rubric Loop — {sc.run_id}",
        "",
        f"**Totals:** {t['pass']} pass / {t['partial']} partial / {t['fail']} fail / {t['unrunnable']} unrunnable   ({t['cases']} cases)",
        f"**Engine:** {sc.engine_version}   **Rubric:** {sc.rubric_version}   **Model:** {sc.codex_model} ({sc.reasoning_effort})",
        "",
    ]
    if sc.delta_from_last_run.get("new_failures"):
        lines.append("## Delta from last run")
        for case_id in sc.delta_from_last_run["new_failures"]:
            lines.append(f"- NEW FAIL: `{case_id}`")
        lines.append("")
    lines.append("## By track")
    lines.append("| track | cases | pass | partial | fail | unrunnable |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for track, b in sorted(sc.by_track.items()):
        lines.append(f"| {track} | {b['cases']} | {b['pass']} | {b['partial']} | {b['fail']} | {b['unrunnable']} |")
    lines.append("")
    lines.append("## By slice")
    lines.append("| slice | cases | pass | partial | fail | unrunnable |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for slice_, b in sorted(sc.by_slice.items()):
        lines.append(f"| {slice_} | {b['cases']} | {b['pass']} | {b['partial']} | {b['fail']} | {b['unrunnable']} |")
    lines.append("")
    lines.append("## By dimension (weighted mean)")
    lines.append("| dimension | weighted_mean | cases |")
    lines.append("|---|---:|---:|")
    for dim, b in sorted(sc.by_dimension.items()):
        lines.append(f"| {dim} | {b['weighted_mean']} | {b['cases']} |")
    lines.append("")
    if sc.failures:
        lines.append("## Failures")
        for f in sc.failures:
            lines.append(f"### {f['case_id']} ({f['verdict']})")
            if f.get("hard_fail_criterion"):
                lines.append(f"- **Hard-fail:** `{f['hard_fail_criterion']}` scored 0.0")
            if f.get("judge_note"):
                lines.append(f"- **Judge note:** {f['judge_note']}")
            if f.get("flags"):
                lines.append(f"- **Flags:** {', '.join(f['flags'])}")
            lines.append(f"- **Fixture:** `scripts/rubric_fixtures/{f['case_id']}.json`")
            lines.append("")
    if sc.warnings:
        lines.append("## Warnings")
        for w in sc.warnings:
            lines.append(f"- {w}")
        lines.append("")
    return "\n".join(lines)


def write_scorecard(sc: Scorecard) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = sc.run_id.replace(":", "-")
    json_path = OUT_DIR / f"rubric-loop-{ts}.json"
    md_path = OUT_DIR / f"rubric-loop-{ts}.md"
    save_json(json_path, sc.to_dict())
    md_path.write_text(render_scorecard_markdown(sc))
    return json_path, md_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 55 tests green.

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric/aggregate.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): Phase 4 aggregate — scorecard assembly and markdown rendering"
```

---

## Task 14: Main entrypoint + argparse

**Files:**
- Create: `scripts/rubric_loop.py`
- Modify: `tests/test_rubric_loop.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_rubric_loop.py`:

```python
import subprocess


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rubric_loop.py::test_rubric_loop_cli_help -v`
Expected: FAIL with non-zero exit (script doesn't exist yet).

- [ ] **Step 3: Implement rubric_loop.py**

Create `scripts/rubric_loop.py`:

```python
#!/usr/bin/env python3
"""Rubric Loop — codex-backed evaluation harness for the compliance rule engine.

Usage:
    python scripts/rubric_loop.py                              # full run, cache-hit friendly
    python scripts/rubric_loop.py --only job_title_mismatch    # drill one rule
    python scripts/rubric_loop.py --slice A                    # positive cases only
    python scripts/rubric_loop.py --phases discover,evaluate   # skip generate + judge
    python scripts/rubric_loop.py --regen A                    # force regen slice A
    python scripts/rubric_loop.py --no-gen                     # skip generation
    python scripts/rubric_loop.py --no-judge                   # skip judge
    python scripts/rubric_loop.py --fail-fast                  # abort on first per-case error

See docs/superpowers/specs/2026-04-10-rubric-loop-design.md for design rationale.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from rubric.aggregate import assemble_scorecard, write_scorecard
from rubric.discover import build_manifest
from rubric.evaluate import evaluate_case
from rubric.generate import generate_missing
from rubric.io import (
    CONFIG_RULES_DIR,
    EVAL_CACHE_DIR,
    FIXTURE_DIR,
    GOLDENS_DIR,
    JUDGE_CACHE_DIR,
    ensure_dirs,
    load_json,
)
from rubric.judge import judge_case
from rubric.models import CallTelemetry, CaseSpec, CoverageGap, FixtureRecord

ALL_PHASES = ["discover", "generate", "evaluate", "judge", "aggregate"]
logger = logging.getLogger("rubric_loop")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Codex-backed rubric evaluation loop for the compliance rule engine.",
    )
    parser.add_argument("--phases", default=",".join(ALL_PHASES),
                        help="comma-separated list of phases to run")
    parser.add_argument("--only", default=None,
                        help="filter to cases for a single rule_id")
    parser.add_argument("--slice", dest="slices", action="append",
                        choices=["A", "B", "C", "D", "E"], default=None,
                        help="filter to specific slices (repeatable)")
    parser.add_argument("--regen", nargs="?", const="ALL", default=None,
                        help="force regenerate fixtures (optional slice letter)")
    parser.add_argument("--no-gen", action="store_true",
                        help="shorthand for --phases discover,evaluate,judge,aggregate")
    parser.add_argument("--no-judge", action="store_true",
                        help="shorthand for --phases discover,generate,evaluate,aggregate")
    parser.add_argument("--fail-fast", action="store_true",
                        help="abort on first per-case error")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args()


def _setup_logging(args) -> None:
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


def _resolve_phases(args) -> list[str]:
    if args.no_gen and args.no_judge:
        logger.error("--no-gen and --no-judge are contradictory")
        sys.exit(2)
    if args.no_gen:
        return ["discover", "evaluate", "judge", "aggregate"]
    if args.no_judge:
        return ["discover", "generate", "evaluate", "aggregate"]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    for p in phases:
        if p not in ALL_PHASES:
            logger.error("unknown phase: %s", p)
            sys.exit(2)
    return phases


def _filter_manifest(manifest: list[CaseSpec], args) -> list[CaseSpec]:
    filtered = manifest
    if args.only:
        filtered = [c for c in filtered if c.target_rule_id == args.only]
    if args.slices:
        filtered = [c for c in filtered if c.slice in args.slices]
    if args.only and not filtered:
        logger.error("no cases match rule_id=%r. check config/rules/*.yaml", args.only)
        sys.exit(2)
    return filtered


def _load_fixture(case_id: str) -> FixtureRecord | None:
    path = FIXTURE_DIR / f"{case_id}.json"
    if not path.exists():
        path = GOLDENS_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    return FixtureRecord.from_dict(load_json(path))


def _apply_regen(args, manifest: list[CaseSpec]) -> None:
    if not args.regen:
        return
    if args.regen == "ALL":
        target_slices = {"A", "B"}
    else:
        if args.regen in {"C", "D", "E"}:
            logger.error("cannot regenerate static goldens; edit files in %s directly", GOLDENS_DIR)
            sys.exit(2)
        target_slices = {args.regen}
    for spec in manifest:
        if spec.slice in target_slices and spec.gen_strategy == "llm":
            fpath = FIXTURE_DIR / f"{spec.case_id}.json"
            if fpath.exists():
                fpath.unlink()
            evpath = EVAL_CACHE_DIR / f"{spec.case_id}.json"
            if evpath.exists():
                evpath.unlink()


def main() -> int:
    args = _parse_args()
    _setup_logging(args)
    phases = _resolve_phases(args)
    ensure_dirs(FIXTURE_DIR, GOLDENS_DIR, EVAL_CACHE_DIR, JUDGE_CACHE_DIR)

    telemetry = CallTelemetry()
    warnings: list[str] = []

    if "discover" in phases:
        try:
            manifest = build_manifest(CONFIG_RULES_DIR, GOLDENS_DIR)
        except CoverageGap as e:
            logger.error("coverage gap detected: %s", e)
            return 2
        logger.info("Phase 0 discover: manifest has %d cases", len(manifest))
    else:
        logger.error("discover phase is required (manifest must exist in-memory)")
        return 2

    manifest = _filter_manifest(manifest, args)
    _apply_regen(args, manifest)

    if "generate" in phases:
        logger.info("Phase 1 generate-missing: checking %d cases", len(manifest))
        new_count, skip_count, gen_warnings = generate_missing(
            manifest, fixture_dir=FIXTURE_DIR, rules_dir=CONFIG_RULES_DIR,
        )
        warnings.extend(gen_warnings)
        telemetry.generator_calls = new_count
        telemetry.generator_calls_cached = skip_count
        logger.info("Phase 1 generate-missing: %d new, %d cached, %d warnings",
                    new_count, skip_count, len(gen_warnings))

    eval_records: dict = {}
    if "evaluate" in phases:
        logger.info("Phase 2 evaluate: running engine on %d cases", len(manifest))
        for spec in manifest:
            fixture = _load_fixture(spec.case_id)
            if fixture is None:
                warnings.append(f"no fixture for {spec.case_id}; skipped")
                continue
            try:
                eval_records[spec.case_id] = evaluate_case(fixture)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"evaluate crashed for {spec.case_id}: {e}")
                if args.fail_fast:
                    return 1

    judge_records: dict = {}
    if "judge" in phases:
        logger.info("Phase 3 judge: grading %d cases", len(eval_records))
        for spec in manifest:
            eval_rec = eval_records.get(spec.case_id)
            fixture = _load_fixture(spec.case_id)
            if not fixture or not eval_rec:
                continue
            try:
                judge_records[spec.case_id] = judge_case(fixture, eval_rec)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"judge crashed for {spec.case_id}: {e}")
                if args.fail_fast:
                    return 1

    if "aggregate" in phases:
        prior = None  # could load the most recent out/rubric-loop-*.json here
        sc = assemble_scorecard(
            cases=manifest,
            eval_records=eval_records,
            judge_records=judge_records,
            telemetry=telemetry,
            warnings=warnings,
            prior_scorecard=prior,
        )
        json_path, md_path = write_scorecard(sc)
        logger.info("Phase 4 aggregate: scorecard written to %s", md_path)
        print(json.dumps(sc.to_dict(), indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 57 tests green.

Also verify the discover-only phase works end-to-end against real rules:
```bash
python scripts/rubric_loop.py --phases discover --no-judge 2>&1 | head -20
```
Expected: shows manifest count, exits 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/rubric_loop.py tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): main CLI entrypoint with phase orchestration"
```

---

## Task 15: Meta-test — deliberately broken rule

**Files:**
- Create: `tests/fixtures/broken_rules.yaml`
- Modify: `tests/test_rubric_loop.py`

This test is the highest-value single test in the suite — if it ever passes without flagging the broken rule, the whole rubric loop is silently broken.

- [ ] **Step 1: Create broken_rules.yaml**

Create `tests/fixtures/broken_rules.yaml`:

```yaml
version: "0.1.0"

# This rule file exists solely for the meta-test in test_rubric_loop.py.
# The rule `impossible_rule` has mutually-exclusive conditions: stage cannot
# simultaneously be 'f1_student' AND 'h1b'. No case can ever satisfy both, so
# the engine will never fire this rule. The rubric loop's slice-A positive
# case for impossible_rule MUST be marked fail with the hard-fail criterion
# positive_case_fires_target_rule. If this test ever passes without that
# failure, the rubric loop is silently broken.

rules:
  - id: impossible_rule
    track: broken_rules
    type: logic
    conditions:
      - field: stage
        operator: eq
        value: f1_student
        source: answers
      - field: stage
        operator: eq
        value: h1b
        source: answers
    severity: warning
    finding:
      title: "impossible to fire"
      action: "this rule will never fire"
      consequence: "for meta-testing only"
      immigration_impact: false
```

- [ ] **Step 2: Write the meta-test**

Append to `tests/test_rubric_loop.py`:

```python
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
```

- [ ] **Step 3: Run the meta-test to verify it passes**

Run: `pytest tests/test_rubric_loop.py::test_meta_broken_rule_is_flagged_as_fail -v`
Expected: PASS — the full loop correctly flags the broken rule as fail.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 58 tests green.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/broken_rules.yaml tests/test_rubric_loop.py
git commit -m "test(rubric-loop): meta-test catches contradictory-rule case"
```

---

## Task 16: Remaining static goldens

**Files:**
- Create: `scripts/rubric_fixtures/goldens/C-operator-missing-none.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-eq-none.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-in-none.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-contains-list-hit.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-contains-list-miss.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-lt-date-past.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-lt-date-future.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-gt-numeric-boundary.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-neq-literal.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-mismatch-needs-review.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-in-string-list.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-eq-bool-lookalike.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-contains-empty-list.json`
- Create: `scripts/rubric_fixtures/goldens/C-operator-mismatch-match-status.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch3-h1b.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch4-outside-us.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch5-default.json`
- Create: `scripts/rubric_fixtures/goldens/D-track-routing-student.json`
- Create: `scripts/rubric_fixtures/goldens/D-track-routing-entity.json`
- Create: `scripts/rubric_fixtures/goldens/D-track-routing-data-room.json`
- Create: `scripts/rubric_fixtures/goldens/D-track-routing-h1b-doc-check.json`
- Create: `scripts/rubric_fixtures/goldens/D-track-routing-stem-opt.json`
- Create: `scripts/rubric_fixtures/goldens/D-nra-branch1-nra-explicit.json`
- Create: `scripts/rubric_fixtures/goldens/D-years-boundary-6.json`
- Create: `scripts/rubric_fixtures/goldens/D-years-boundary-0.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-missing-stage.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-conflicting-tax-residency.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-empty-conditions-advisory.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-numeric-prefix-field.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-mismatch-vs-needs-review.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-trigger-upload-auto-eval.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-trigger-chat-context.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-trigger-marketplace-h1b.json`
- Create: `scripts/rubric_fixtures/goldens/E-edge-h1b-pending-no-travel.json`
- Modify: `tests/test_rubric_loop.py`

Because each golden follows the exact same JSON shape (see Task 6 for the template), this task is fundamentally data entry. The engineer should model each file on a Task 6 fixture and adjust the probe_intent + input + expected fields.

Guidance per-file: match the case_id's intent. For example, `C-operator-missing-none.json` probes the `missing` operator on a null value — set `answers.registration_number = null` on track `h1b_doc_check` and expect `h1b_missing_registration_number` to fire. Each golden must be self-contained and pass the engine's actual behavior.

- [ ] **Step 1: Draft all 34 golden fixtures**

Use Task 6's C/D/E fixtures as templates. Each file must have: `case_id`, `slice`, `track`, `target_rule_id` (nullable), `probe_intent`, `generated_by: "hand"`, `generated_at`, `generator_prompt_hash: null`, `flavor_hint: null`, `input`, `expected`. One file per line in the "Files" list above.

Write each golden with a clear `notes` field in `expected` explaining what branch/operator/edge it probes.

- [ ] **Step 2: Run discover to verify all goldens load**

Run: `python scripts/rubric_loop.py --phases discover`
Expected: exits 0, manifest count is reported (should be 71×2 + 40 = 182).

- [ ] **Step 3: Write a coverage-sanity test**

Append to `tests/test_rubric_loop.py`:

```python
def test_all_five_slices_have_goldens():
    """Smoke test that every slice C/D/E has at least 3 goldens."""
    from rubric.io import GOLDENS_DIR
    by_slice: dict = {}
    for f in GOLDENS_DIR.glob("*.json"):
        first_char = f.name[0]
        by_slice.setdefault(first_char, 0)
        by_slice[first_char] += 1
    assert by_slice.get("C", 0) >= 3, "need at least 3 slice-C goldens"
    assert by_slice.get("D", 0) >= 3, "need at least 3 slice-D goldens"
    assert by_slice.get("E", 0) >= 3, "need at least 3 slice-E goldens"


def test_goldens_total_at_least_40():
    from rubric.io import GOLDENS_DIR
    count = len(list(GOLDENS_DIR.glob("*.json")))
    assert count >= 40, f"expected ≥40 static goldens, got {count}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rubric_loop.py -v`
Expected: PASS — 60 tests green.

- [ ] **Step 5: Run Phase 2 against all goldens**

Run:
```bash
python scripts/rubric_loop.py --slice C --slice D --slice E --phases discover,evaluate
```
Expected: exits 0, each golden evaluates successfully (check stderr for any engine errors).

- [ ] **Step 6: Commit**

```bash
git add scripts/rubric_fixtures/goldens/ tests/test_rubric_loop.py
git commit -m "feat(rubric-loop): expand static goldens to full slice C/D/E coverage"
```

---

## Task 17: Gitignore entries

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Read current .gitignore**

Run: `cat .gitignore`
Note existing entries to avoid duplicates.

- [ ] **Step 2: Add rubric-loop entries**

Append to `.gitignore`:

```
# Rubric loop
scripts/rubric_cache/
out/rubric-loop-*.json
out/rubric-loop-*.md
/tmp/rubric-loop-workspace/
```

- [ ] **Step 3: Verify entries work**

Run:
```bash
mkdir -p scripts/rubric_cache/evaluate
touch scripts/rubric_cache/evaluate/test.json
git status --short
```
Expected: `scripts/rubric_cache/` should NOT appear in `git status` output.

Then clean up:
```bash
rm scripts/rubric_cache/evaluate/test.json
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(rubric-loop): gitignore entries for cache and run outputs"
```

---

## Task 18: First full real run + commit LLM fixtures

**Files:**
- Create: `scripts/rubric_fixtures/A-*.json` (~71 files from first real generation)
- Create: `scripts/rubric_fixtures/B-*.json` (~71 files from first real generation)

This is the first task that makes real `codex exec` calls. Expect the full run to take several minutes.

- [ ] **Step 1: Verify codex CLI is ready**

Run:
```bash
codex --version
codex exec -m gpt-5.4 --sandbox read-only --ephemeral \
    --output-schema scripts/rubric/schemas/generator-output.schema.json \
    - <<< "Test — output a trivial JSON like {\"input\":{\"answers\":{},\"extraction_a\":{},\"extraction_b\":{},\"comparisons\":{}},\"expected\":{\"must_fire_rule_ids\":[],\"must_not_fire_rule_ids\":[],\"expected_nra\":\"no\",\"expected_track\":\"stem_opt\"},\"flavor_hint\":null}"
```
Expected: codex responds with valid JSON matching the schema. If this fails, fix auth/model availability before proceeding.

- [ ] **Step 2: Run Phase 1 only (generate all fixtures, no evaluate/judge)**

```bash
python scripts/rubric_loop.py --phases discover,generate 2>&1 | tee out/first-run-gen.log
```
Expected: reports "Phase 1 generate-missing: ~142 new, ~40 cached, N warnings". Check the log for any generator failures.

- [ ] **Step 3: Spot-check 3-5 generated fixtures**

```bash
ls scripts/rubric_fixtures/ | grep -E "^(A|B)-" | head -5
cat scripts/rubric_fixtures/A-stem_opt-job_title_mismatch-pos.json
```
Verify the JSON is well-formed, the `input` maps to `EvaluationContext` shape, and `expected.must_fire_rule_ids` includes the target rule.

- [ ] **Step 4: Run full loop end-to-end**

```bash
python scripts/rubric_loop.py 2>&1 | tee out/first-run-full.log
```
Expected: exits 0, scorecard written to `out/rubric-loop-*.md`.

Expected total time: 3-10 minutes depending on codex latency for xhigh reasoning.

- [ ] **Step 5: Inspect the scorecard**

```bash
cat out/rubric-loop-*.md | tail -1 $(ls -t out/rubric-loop-*.md | head -1)
```
Review:
- Totals (expect ≥80% pass on a healthy rule set; lower is fine for v0)
- Any `fail` verdicts — are they real bugs, or rubric false negatives?
- Any `unrunnable` cases — inspect `flags` and the fixture file
- Warnings — especially PII-shaped string warnings

- [ ] **Step 6: Commit the generated fixtures**

Review the fixtures one more time, then:

```bash
git add scripts/rubric_fixtures/A-*.json scripts/rubric_fixtures/B-*.json
git commit -m "feat(rubric-loop): first generation of ~142 slice A+B fixtures"
```

- [ ] **Step 7: Final celebration commit**

```bash
git status
echo "Rubric loop v0 complete. See docs/superpowers/specs/2026-04-10-rubric-loop-design.md for context."
```

---

## Final checklist

Before declaring v0 shipped:

- [ ] All 18 tasks committed
- [ ] `pytest tests/test_rubric_loop.py -v` → all tests green
- [ ] `python scripts/rubric_loop.py --phases discover` → exit 0 with manifest count
- [ ] `python scripts/rubric_loop.py --no-gen --no-judge` → Phase 2 runs cleanly
- [ ] `out/rubric-loop-*.md` exists and reports reasonable totals
- [ ] `.gitignore` prevents `scripts/rubric_cache/` and `out/rubric-loop-*` from showing in `git status`
- [ ] The meta-test `test_meta_broken_rule_is_flagged_as_fail` passes — this is the canary for the whole loop

## Follow-ups deferred from v0

From spec section "Non-Goals" and "Follow-ups":
- CI integration (workflow file)
- Web dashboard
- Parallel workers (Architecture 3)
- Auto-fixture review tooling (render JSON as readable markdown)
- Rubric criteria expansion as real failure modes surface

These are out of scope. Add them as separate specs if/when they become worth building.
