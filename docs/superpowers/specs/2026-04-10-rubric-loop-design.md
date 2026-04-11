# Rubric Loop: Codex-Backed Evaluation Harness for the Compliance Rule Engine

**Date:** 2026-04-10
**Status:** Draft — pending user review
**Related:**
- `compliance_os/web/services/rule_engine.py` (the engine under test)
- `config/rules/*.yaml` (the rule set under test)
- `scripts/extraction_bakeoff.py` (sibling bakeoff script whose structure this mirrors)
- `scripts/codex_loop/` (existing agentic codex loop — parallel pattern, different use case)

## Overview

Build a **rough-style evaluation loop** that systematically exercises Guardian's deterministic YAML rule engine across its full input space and grades its behavior using `codex` CLI as an LLM-as-judge. The loop produces a scorecard identifying where rules fire incorrectly, where categorization logic routes wrong, and where the rule set itself contains latent quality problems.

Unlike a traditional unit-test suite, this harness treats the engine as a black box and scores its behavior against a declarative rubric — allowing the rubric to evolve independently of the engine and surfacing classes of bugs that fixture-based assertions miss (cross-rule contradictions, severity miscalibration, rule-text ambiguity, type-coercion gotchas).

The design covers three layers of engine behavior in a single loop:

1. **Categorization** — did we route the case to the right track (stem_opt / student / entity / data_room / h1b_doc_check) and derive fields like `is_nra` correctly?
2. **Findings** — did the rules fire correctly given the inputs? Both polarities: did the right rules fire, and did wrong rules stay quiet?
3. **Rule-set quality** — are the rules themselves actionable, non-contradictory, and well-specified?

Coverage is exhaustive by equivalence class: ~71 rules × 2 polarities + ~40 static edge-case goldens = **~182 total cases per full run**.

## Goals

- **Exhaustively cover the engine's input space** via equivalence classes: every rule in both polarities, every operator, every `_derive_nra` branch, every track-routing path, and every known value-type edge case.
- **Surface rule-set bugs that unit tests miss** — cross-rule contradictions, severity miscalibration, unreachable conditions, value-type gotchas (e.g., `form_5472_present: "False"` string-vs-bool).
- **Support fast iteration** — tweak a rule YAML, re-run, see only the cases whose engine output actually changed get re-judged. Full re-judging only when the rubric itself changes.
- **Stay hermetic** — no real user data touches the generator or judge. No PII exposure through codex calls. All rule knowledge passes through the prompt, not through file access.
- **Auto-discover new rules** — adding a rule to a YAML file automatically grows coverage. The loop refuses to run if any rule has no covering case.
- **Produce a deterministic scorecard** — given stable fixtures, stable rules, stable rubric, and cache hits, the scorecard is byte-identical across runs.

## Non-Goals

- **No CI integration in v0.** The loop can be invoked from CI later via `--phases evaluate,judge,aggregate --fail-fast`, but v0 does not ship a GitHub Actions workflow.
- **No web dashboard.** Scorecard output is markdown + JSON. Visualization is someone else's problem.
- **No auto-generation of rubric criteria.** Criteria are human-authored in `config/rubric/criteria.yaml`. The loop never proposes new criteria.
- **No auto-fixing of failing rules.** The loop reports, never edits. If a fail surfaces a bug in `entity.yaml`, fixing it is a separate human task.
- **No regeneration of goldens.** Edge-case golden fixtures are human-authored ground truth; the loop never touches them.
- **No parallel workers in v0.** Sequential execution only. Parallel fan-out is available if wall-clock becomes an issue.
- **No reuse of real user data (including test@123.com).** The engine is exercised purely on synthetic fixtures — hermetic by design.

## Key Decisions (with rationale)

This section captures the fork-points from the brainstorming dialogue so future readers can see *why* the design looks the way it does, not just *what* it is.

### D1. What does the judge evaluate? → **All three layers** (categorization + findings + rule quality)

**Considered:** findings-only (classic eval), rule-set-only (meta-lint), categorization-only, all three.
**Chosen:** all three, in a single loop, with dimension-weighted subscores. A rubric that only scores finding output misses the higher-leverage class of errors in the *categorization layer* (wrong track selection, wrong NRA derivation) and in the *rule set itself* (contradictions, unreachable conditions).

### D2. Ground-truth strategy → **Generator proposes intent, judge ratifies**

**Considered:**
- (A) Generator self-labels expected findings (brittle to rule renames)
- (B) Rubric-only judging with no ground truth (robust but criterion-based, not exact-match)
- (C) Hybrid — generator labels AND rubric grades (two judge passes)
- (D) Generator outputs case + probe intent, judge evaluates engine response against probe

**Chosen:** D. Each case carries a factual `probe_intent` describing what it's testing. The judge sees the case, the engine output, and the probe intent, and grades whether the engine responded appropriately. Less brittle than exact-match, more debuggable than pure rubric-only scoring, no collusion between generator and judge since each operates on disjoint knowledge.

### D3. Coverage strategy → **Equivalence classes, auto-discovered from YAML** (~182 cases)

**Considered:** literal Cartesian (millions of combinations, nonsensical), per-rule fuzzing (~1000 cases, low marginal signal), positive-only (~80 cases, leaves negative false positives uncaught), equivalence classes (~180 cases, full coverage).
**Chosen:** equivalence classes with a strict `CoverageGap` invariant — if any rule in any YAML has no covering case, the run aborts before any codex calls. New rules automatically grow coverage.

### D4. Generator input source → **Rule YAMLs + synthetic only; NO real user data**

**Considered:** seed generator with test@123.com account documents to get realistic shapes.
**Chosen:** synthetic only. Three reasons:
1. **The YAMLs are already the source of truth** — a grep of `field:` across `config/rules/*.yaml` yields all 52 fields the engine can read. Any extra fields are ignored at `Condition._resolve`.
2. **PII exposure** — codex CLI calls leave the machine; piping real data (even from a nominally "test" account) through it turns the rubric harness into a quiet data-exfil channel.
3. **Over-fitting** — real data doesn't exercise edge cases like `value: "False"` string gotchas or boundary `years_in_us` values. Synthetic is strictly better for the corners where rubric loops earn their keep.

Generator is given a field reference table built from the YAML grep plus derivation notes from `_derive_nra`. No file access, no repo context.

### D5. Loop location and invasiveness → **`scripts/rubric_loop.py`, zero touch to engine**

**Considered:** new script with engine instrumentation, pytest integration.
**Chosen:** new script, sibling to `scripts/extraction_bakeoff.py`, zero changes to `compliance_os/`. Matches the house bakeoff style.

### D6. Loop architecture → **Phased with fixture cache**

**Considered:** sequential streaming (simple but non-deterministic, slow iteration), rule-parallel fan-out (complex, rate-limit concerns).
**Chosen:** four phases (discover → generate-missing → evaluate → judge → aggregate) with an on-disk fixture cache (committed to git) and evaluate/judge caches (gitignored). First run generates all ~182 fixtures and judges them; subsequent runs cache-hit everything except cases whose engine output actually changed. Reproducibility invariant: identical inputs → byte-identical scorecard.

### D7. Synthetic data framing → **PII-free synthetic, styling optional** (not "joke data")

**Considered:** mandatory joke/absurd framing for all synthetic cases.
**Chosen:** synthetic-and-PII-free is the only hard requirement. Playful, realistic, or deadpan flavor is optional and the generator picks whichever best illustrates the probe intent. Static goldens (slices C/D/E) default to plain because precision edge-case tests don't benefit from humor.

### D8. Codex model → **`gpt-5.4` xhigh, fallback `gpt-5.4-mini`**

**Considered:** `gpt-5.3-codex` (coding-specialized, house default in `scripts/codex_loop/`).
**Chosen:** `gpt-5.4` with `model_reasoning_effort=xhigh`. Rationale: the rubric loop generates structured JSON about compliance rule semantics and judges reasoning about rule behavior — neither is a coding task. The coding-specialized variant would be a mismatched tool even if it migrates to the same endpoint today. Fallback stays within the general-purpose family (`gpt-5.4-mini`), not the coding family, to preserve the "not a coding task" invariant if the primary model becomes unavailable.

Codex CLI is subscription-billed for this user, so cost is not a selection criterion.

## Architecture

### Phase structure

```
┌──────────────────────────────────────┐
│  Phase 0: Discover                   │   (pure, no external calls)
│  • Read config/rules/*.yaml          │
│  • Build case manifest:              │
│    - slice A+B auto (A-pos + B-neg)  │
│    - slice C/D/E from static goldens │
│  • Enforce CoverageGap invariant     │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Phase 1: Generate-missing            │  (codex calls for new cases only)
│  • For each case in manifest:        │
│    - if fixture exists → skip        │
│    - else → codex generate → save    │
│  • Slice C/D/E never regenerated     │
│  • Per-case errors isolated          │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Phase 2: Evaluate                    │  (local engine runs, <1s total)
│  • For each fixture:                 │
│    - build EvaluationContext         │
│    - RuleEngine.from_yaml(track)     │
│    - .evaluate(ctx) → findings       │
│  • Capture engine_error for slice-C  │
│  • Write to rubric_cache/evaluate/   │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Phase 3: Judge                       │  (codex calls, cache-hit friendly)
│  • For each (case, findings) pair:   │
│    - compute cache key               │
│    - if cache hit → skip             │
│    - else → codex judge → save       │
│  • Cache key =                       │
│    hash(input, findings,             │
│         rubric_version,              │
│         judge_prompt_hash)           │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│  Phase 4: Aggregate                   │  (pure, no external calls)
│  • Totals by track / slice / dim     │
│  • Coverage gap report               │
│  • Delta from last run               │
│  • Write out/rubric-loop-<ts>.{md,json} │
└──────────────────────────────────────┘
```

**Invariants between phases:**
- Phase 0 is pure — no external calls, no cache writes. Detects misconfiguration before any codex spend.
- Phase 1 is the only phase that calls the generator. Can be skipped entirely via `--no-gen`.
- Phase 2 never calls codex. Deterministic, local, fast.
- Phase 3 is the only phase that calls the judge. Can be skipped via `--no-judge` for engine-output-only runs.
- Phase 4 is pure aggregation. Always writes a scorecard unless an upstream phase caused a global abort.

Each phase can be run in isolation via `--phases`:
```
python scripts/rubric_loop.py --phases discover,generate     # only populate fixture cache
python scripts/rubric_loop.py --phases evaluate,judge         # re-score cached cases
python scripts/rubric_loop.py                                 # full run with cache hits
python scripts/rubric_loop.py --only job_title_mismatch       # drill one rule
python scripts/rubric_loop.py --slice A                       # positive cases only
python scripts/rubric_loop.py --regen A                       # force regenerate slice A
```

## File Layout

```
scripts/
├── rubric_loop.py                    # main entry point, argparse, orchestration (~150 lines)
├── rubric/                           # helper package
│   ├── __init__.py
│   ├── discover.py                   # Phase 0: YAML → case manifest
│   ├── generate.py                   # Phase 1: codex generator invocation
│   ├── evaluate.py                   # Phase 2: engine runs
│   ├── judge.py                      # Phase 3: codex judge invocation
│   ├── aggregate.py                  # Phase 4: scorecard assembly
│   ├── codex_client.py               # thin wrapper around `codex exec`
│   ├── case_ids.py                   # canonical case_id generation
│   ├── hints.py                      # generator-hints builder from YAMLs
│   ├── prompts/
│   │   ├── generator.md              # generator system + user template
│   │   └── judge.md                  # judge system + user template
│   └── schemas/
│       ├── generator-output.schema.json
│       └── judge-output.schema.json
├── rubric_fixtures/                  # PHASE 1 OUTPUT (committed to git)
│   ├── A-stem_opt-job_title_mismatch-pos.json
│   ├── B-stem_opt-job_title_mismatch-neg.json
│   ├── A-student-cpt_employer_mismatch-pos.json
│   ├── ... (~142 LLM-generated)
│   └── goldens/                      # STATIC, hand-written (committed)
│       ├── C-operator-contains-scalar.json
│       ├── C-operator-gt-malformed-date.json
│       ├── D-nra-branch1-explicit.json
│       ├── D-nra-branch2-f1-exempt-boundary.json
│       ├── E-edge-empty-context.json
│       ├── E-edge-false-string-gotcha.json
│       └── ... (~40 hand-written)
└── rubric_cache/                     # GITIGNORED
    ├── evaluate/                     # (case_id → findings) JSON
    └── judge/                        # (cache_key → judge result) JSON

config/
└── rubric/                           # committed
    ├── criteria.yaml                 # the rubric the judge applies
    └── rubric_version.txt            # single-line semver; bump → invalidate judge cache

tests/
└── test_rubric_loop.py               # unit + integration tests for the harness itself

out/
├── rubric-loop-2026-04-10-142301.md  # scorecard (gitignored)
└── rubric-loop-2026-04-10-142301.json
```

**Design choices worth calling out:**

- **`scripts/rubric/` as a package** keeps the main script small and testable. Each helper module has one purpose.
- **`rubric_fixtures/goldens/` as a sibling directory** (not a flag on individual files) lets Phase 1 skip goldens by directory glob — no chance of accidentally regenerating a hand-written case.
- **`config/rubric/`** lives next to `config/rules/` because it's configuration of the rubric in the same sense rules are configuration of the engine.
- **`rubric_cache/` is gitignored** because it's pure computation derivable from the fixtures, rule YAMLs, and rubric version. Committing it would be noise.
- **Fixtures committed to git** for code-review visibility, regression tracking, and CI reuse. Can be gitignored later if churn becomes an issue.
- **`out/`** matches existing project convention (`scripts/bakeoff_results/` is similar).

## Case Enumeration: The Input Space

The engine's input space factors into **13 dimensions** that collapse into ~182 canonical equivalence-class cases.

### The 13 dimensions

| # | Dimension | Values | Source |
|---|---|---|---|
| 1 | **Track** | `stem_opt`, `student`, `entity`, `data_room`, `h1b_doc_check` | routers/review.py:606-633, 5 YAML files |
| 2 | **Stage** | `f1_student`, `opt`, `stem_opt`, `h1b`, `i140`, `pre_completion` | rule_engine.py:26 |
| 3 | **NRA status** | `yes`, `no`, ambiguous | rule_engine.py:29-58 |
| 4 | **Document extraction presence** | full, partial, empty, malformed | EvaluationContext fields |
| 5 | **Comparison outcomes** | `match`, `mismatch`, `needs_review`, absent | rule_engine.py:86-89 |
| 6 | **Operators** | `mismatch`, `missing`, `eq`, `neq`, `gt`, `lt`, `in`, `contains` | rule_engine.py:86-110 |
| 7 | **Date-relative values** | `today`, `N_months_ago`, `N_days_from_now`, literal | rule_engine.py:125-134 |
| 8 | **Multi-condition AND** | 0, 1, 2, 3+ conditions | student.yaml uses 0, entity.yaml uses 3 |
| 9 | **Rule type** | `comparison`, `logic`, `advisory`, `completeness`, `inconsistency`, `timing` | union across 5 YAMLs |
| 10 | **Severity** | `critical`, `warning`, `info` | rule_engine.py:222 |
| 11 | **Immigration impact** | `true`, `false` | finding metadata; default False |
| 12 | **Trigger site** | POST /review, upload auto-eval, chat context, marketplace H-1B | review.py:646, dashboard.py:528, chat.py:438, h1b_doc_check.py:182 |
| 13 | **Value-type gotchas** | bool vs `"False"` string, numeric vs string dates, list vs scalar for `contains` | entity.yaml `missing_5472`, entity.yaml `schedule_c_on_opt` |

### Rule inventory

| Track | Rules | Comparison | Logic | Advisory | Completeness | Inconsistency | Timing |
|---|---:|---:|---:|---:|---:|---:|---:|
| `stem_opt` | 23 | 6 | 13 | 4 | — | — | — |
| `student` | 13 | 4 | 6 | 3 | — | — | — |
| `entity` | 16 | — | 8 | 8 | — | — | — |
| `data_room` | 12 | 12 | — | — | — | — | — |
| `h1b_doc_check` | 7 | — | — | — | 2 | 4 | 1 |
| **Total** | **71** | **22** | **27** | **15** | **2** | **4** | **1** |

### Five coverage slices

| Slice | What it probes | Generation | Cases |
|---|---|---|---:|
| **A. Rule-firing positive** | One case per rule whose probe intent is "engine SHOULD fire this rule" | codex | ~71 |
| **B. Rule-firing negative near-miss** | One case per rule whose probe intent is "engine should NOT fire this rule but a naive reader might think it should" | codex | ~71 |
| **C. Operator stress** | Per operator: null, boundary, wrong-type cases | static goldens | ~16 |
| **D. Categorization stress** | Per track: track routing; per `_derive_nra` branch (4): a case hitting exactly that branch | static goldens | ~14 |
| **E. Trigger + edge cases** | One case per trigger site; empty dicts; missing stage; conflicting `tax_residency_status`; boundary `years_in_us`; `conditions: []` advisory; `value: "False"` string gotcha; `1042s_*` numeric-prefix field; `needs_review` vs `mismatch` equivalence | static goldens | ~10 |
| **Total** | | | **~182** |

**Why this covers the space:** Slices A+B give 100% rule-ID coverage in both polarities. Slice C exercises every operator path in `Condition.evaluate`. Slice D exercises every `_derive_nra` priority branch and every track-routing mapping. Slice E pins down the trigger layer and every known YAML landmine. If a rule, operator, branch, or trigger isn't touched by at least one case, the `CoverageGap` invariant fires during Phase 0 and the run aborts.

**Why slices C/D/E are static goldens (not LLM-generated):**
- They test deterministic engine behaviors (e.g., "`contains` on a scalar returns False") where LLM generation adds stochasticity for no benefit.
- They double as regression tests for engine internals — checked into source control, reviewed by humans, immutable across runs.
- This cuts the codex generator bill roughly in half and makes the deterministic parts genuinely deterministic.

### Phase 0 algorithm (pseudocode)

```python
def build_manifest(rule_dir: Path, golden_dir: Path) -> list[CaseSpec]:
    cases = []

    # Slices A + B: one per rule, both polarities
    for yaml_file in sorted(rule_dir.glob("*.yaml")):
        track = yaml_file.stem
        data = yaml.safe_load(yaml_file.read_text())
        for rule in data.get("rules", []):
            rule_id = rule["id"]

            # Slice A: engine MUST fire this rule
            cases.append(CaseSpec(
                case_id=f"A-{track}-{rule_id}-pos",
                slice="A",
                track=track,
                target_rule_id=rule_id,
                target_rule_snapshot=rule,
                probe_intent=build_positive_intent(rule),
                gen_strategy="llm",
            ))

            # Slice B: engine MUST NOT fire this rule — adversarial near-miss
            cases.append(CaseSpec(
                case_id=f"B-{track}-{rule_id}-neg",
                slice="B",
                track=track,
                target_rule_id=rule_id,
                target_rule_snapshot=rule,
                probe_intent=build_negative_intent(rule),
                gen_strategy="llm",
            ))

    # Slices C, D, E: load hand-written goldens verbatim
    for golden_file in sorted(golden_dir.glob("*.json")):
        spec = json.loads(golden_file.read_text())
        cases.append(CaseSpec(
            case_id=spec["case_id"],
            slice=spec["slice"],
            track=spec.get("track"),
            target_rule_id=spec.get("target_rule_id"),
            probe_intent=spec["probe_intent"],
            gen_strategy="golden",
            fixture_content=spec,
        ))

    # CoverageGap invariant: every rule must have ≥1 case
    seen_rule_ids = {c.target_rule_id for c in cases if c.target_rule_id}
    all_rule_ids = set(_all_rule_ids(rule_dir))
    if missing := all_rule_ids - seen_rule_ids:
        raise CoverageGap(f"No cases cover rules: {sorted(missing)}")

    return cases
```

`build_positive_intent(rule)` and `build_negative_intent(rule)` are deterministic — same rule YAML → same intent text → same prompt → same cache key. This is what preserves determinism across runs despite using a stochastic generator: the intent derivation is a pure function.

## Data Contracts

Five shapes live on disk, each with a specific role in the pipeline.

### Fixture file — `scripts/rubric_fixtures/<case_id>.json`

```json
{
  "case_id": "A-stem_opt-job_title_mismatch-pos",
  "slice": "A",
  "track": "stem_opt",
  "target_rule_id": "job_title_mismatch",
  "probe_intent": "Generate a synthetic case where the I-983 and employment letter disagree on job title. The comparisons dict must have job_title: {status: 'mismatch'}. No real PII.",
  "generated_by": "codex-cli@0.118.0/gpt-5.4",
  "generated_at": "2026-04-10T14:22:18Z",
  "generator_prompt_hash": "sha256:4a1f...",
  "flavor_hint": null,
  "input": {
    "answers": {
      "stage": "stem_opt",
      "years_in_us": 3,
      "employer_changed": "no"
    },
    "extraction_a": {
      "job_title": "Senior Platform Engineer",
      "start_date": "2024-06-15",
      "end_date": "2027-06-14"
    },
    "extraction_b": {
      "job_title": "Staff Engineer"
    },
    "comparisons": {
      "job_title": {"status": "mismatch", "confidence": 0.92}
    }
  },
  "expected": {
    "must_fire_rule_ids": ["job_title_mismatch"],
    "must_not_fire_rule_ids": [],
    "expected_nra": "yes",
    "expected_track": "stem_opt",
    "notes": "Titles disagree across I-983 and employment letter; stage+years in NRA branch 2"
  }
}
```

**Field contracts:**

| Field | Contract |
|---|---|
| `case_id` | Canonical ID. Format for A/B: `<slice>-<track>-<rule_id>-<polarity>`. Free-form for C/D/E goldens. |
| `slice` | `"A"`\|`"B"`\|`"C"`\|`"D"`\|`"E"`. Determines which rubric criteria apply. |
| `target_rule_id` | Set for A/B and rule-specific goldens. Null for operator-stress and edge-case goldens. |
| `probe_intent` | Factual description. Styling-neutral. Written by `build_*_intent` for A/B; hand-written for goldens. |
| `generated_by` | `"codex-cli@<version>/<model>"` for LLM, `"hand"` for goldens. Used for traceability. |
| `generator_prompt_hash` | SHA-256 of generator prompt. Hash change → Phase 1 regenerates on next run. |
| `flavor_hint` | Optional, nullable. Free-form (`"playful"`, `"realistic"`, `"deadpan"`). Human-readability only; judge never reads it. |
| `input.*` | Maps 1:1 to `EvaluationContext(answers, extraction_a, extraction_b, comparisons)`. |
| `expected.must_fire_rule_ids` | Soft ground truth. For slice A, includes `target_rule_id`. For slice B, usually empty. |
| `expected.must_not_fire_rule_ids` | Soft ground truth. For slice B, includes `target_rule_id`. |
| `expected.expected_nra` | `"yes"` \| `"no"`. Validates `_derive_nra`. |
| `expected.expected_track` | Validates track routing. |
| `expected.notes` | Optional human-readable explanation; judge sees it. |

### Evaluate cache — `scripts/rubric_cache/evaluate/<case_id>.json`

```json
{
  "case_id": "A-stem_opt-job_title_mismatch-pos",
  "engine_version": "1.0.0",
  "rule_file_path": "config/rules/stem_opt.yaml",
  "rule_file_hash": "sha256:9e2b...",
  "input_hash": "sha256:3c4f...",
  "evaluated_at": "2026-04-10T14:22:19Z",
  "derived": {
    "is_nra": "yes"
  },
  "findings": [
    {
      "rule_id": "job_title_mismatch",
      "severity": "warning",
      "category": "comparison",
      "title": "Job title mismatch between I-983 and employment letter",
      "action": "File an amended I-983 with your DSO using your actual current title",
      "consequence": "RFE trigger",
      "immigration_impact": true
    }
  ],
  "engine_error": null
}
```

**Invalidation:**
- `input_hash` mismatch → re-evaluate (fixture changed)
- `rule_file_hash` mismatch → re-evaluate all cases for that track
- `engine_version` mismatch → re-evaluate everything

`engine_error` captures exceptions from `RuleEngine.evaluate` so slice-C operator-stress cases can be scored on "did it raise the right error" instead of "did it produce the right findings."

### Judge cache — `scripts/rubric_cache/judge/<cache_key>.json`

The caching lynchpin.

```json
{
  "cache_key": "sha256:b17a...",
  "cache_key_inputs": {
    "case_id": "A-stem_opt-job_title_mismatch-pos",
    "input_hash": "sha256:3c4f...",
    "findings_hash": "sha256:d801...",
    "rubric_version": "0.1.0",
    "judge_prompt_hash": "sha256:77e3..."
  },
  "case_id": "A-stem_opt-job_title_mismatch-pos",
  "judged_at": "2026-04-10T14:22:45Z",
  "judged_by": "codex-cli@0.118.0/gpt-5.4",
  "verdict": "pass",
  "subscores": {
    "categorization": {
      "score": 1.0,
      "criteria_applied": ["track_selection_correct", "nra_derivation_correct"],
      "note": "Track stem_opt correctly routed; NRA=yes via derivation branch 2 (F-1 exempt, years<6)."
    },
    "findings": {
      "score": 1.0,
      "criteria_applied": ["positive_case_fires_target_rule", "no_unrelated_false_positives", "severity_matches_case_gravity"],
      "note": "job_title_mismatch fired with severity=warning as expected. No false positives."
    },
    "rule_quality": {
      "score": 0.9,
      "criteria_applied": ["rule_text_actionable", "rule_conditions_non_contradictory"],
      "note": "Action text is concrete. Slight ambiguity in 'your actual current title'."
    }
  },
  "flags": [],
  "raw_judge_output": "...(truncated)..."
}
```

**Cache key construction:**
```python
cache_key = sha256(
    f"{input_hash}|{findings_hash}|{rubric_version}|{judge_prompt_hash}"
).hexdigest()
```

Each axis invalidates the right amount:
- Edit fixture → `input_hash` changes → this case stale
- Edit rule YAML that changes findings → `findings_hash` changes → affected cases stale
- Bump `rubric_version` → all judge results stale (but fixtures + eval cache unaffected)
- Edit judge prompt template → all judge results stale
- Edit rule YAML that doesn't change findings → nothing invalidates → cache hit

**Verdict values:**
- `pass` — weighted mean subscore ≥ 0.90
- `partial` — 0.60 ≤ weighted mean < 0.90
- `fail` — weighted mean < 0.60, OR any hard-fail criterion scored 0.0
- `unrunnable` — engine raised unexpectedly, or judge output couldn't be parsed

### Rubric criteria — `config/rubric/criteria.yaml`

The declarative rubric the judge applies. Bumping `version` invalidates all judge cache entries without touching fixtures or eval cache.

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
  # --- Categorization ---
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

  # --- Findings ---
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

  # --- Rule quality ---
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

  # --- Operator behavior (slice C only) ---
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
    findings: 2.0          # findings is the main event
    rule_quality: 1.0
    operator_behavior: 1.0

  pass_threshold: 0.90
  partial_threshold: 0.60

  hard_fail_criteria:
    - positive_case_fires_target_rule
    - negative_case_does_not_fire_target_rule
    - expected_must_not_fire_respected
```

The judge receives a **filtered** criterion set based on the case's slice. A slice-A case never sees the slice-C operator criteria; a slice-B case never sees rule-text criteria. This keeps judge prompts focused.

### Scorecard — `out/rubric-loop-<timestamp>.{json,md}`

#### JSON shape

```json
{
  "run_id": "2026-04-10T14-22-00Z",
  "engine_version": "1.0.0",
  "rubric_version": "0.1.0",
  "codex_version": "0.118.0",
  "codex_model": "gpt-5.4",
  "reasoning_effort": "xhigh",
  "started_at": "2026-04-10T14:22:00Z",
  "completed_at": "2026-04-10T14:29:15Z",

  "totals": {
    "cases": 182,
    "pass": 167,
    "partial": 11,
    "fail": 3,
    "unrunnable": 1
  },

  "by_track": {
    "stem_opt": {"cases": 46, "pass": 44, "partial": 2, "fail": 0, "unrunnable": 0},
    "student": {"cases": 26, "pass": 25, "partial": 1, "fail": 0, "unrunnable": 0},
    "entity": {"cases": 32, "pass": 29, "partial": 2, "fail": 1, "unrunnable": 0},
    "data_room": {"cases": 24, "pass": 22, "partial": 2, "fail": 0, "unrunnable": 0},
    "h1b_doc_check": {"cases": 14, "pass": 12, "partial": 2, "fail": 0, "unrunnable": 0}
  },

  "by_slice": {
    "A": {"cases": 71, "pass": 65, "partial": 4, "fail": 2, "unrunnable": 0},
    "B": {"cases": 71, "pass": 66, "partial": 3, "fail": 1, "unrunnable": 1},
    "C": {"cases": 16, "pass": 16, "partial": 0, "fail": 0, "unrunnable": 0},
    "D": {"cases": 14, "pass": 12, "partial": 2, "fail": 0, "unrunnable": 0},
    "E": {"cases": 10, "pass": 8,  "partial": 2, "fail": 0, "unrunnable": 0}
  },

  "by_dimension": {
    "categorization": {"weighted_mean": 0.97, "cases": 182},
    "findings": {"weighted_mean": 0.91, "cases": 182},
    "rule_quality": {"weighted_mean": 0.88, "cases": 142},
    "operator_behavior": {"weighted_mean": 1.00, "cases": 16}
  },

  "failures": [
    {
      "case_id": "A-entity-missing_5472-pos",
      "verdict": "fail",
      "dimension_scores": {"categorization": 1.0, "findings": 0.0, "rule_quality": 0.5},
      "hard_fail_criterion": "positive_case_fires_target_rule",
      "judge_note": "Rule missing_5472 did not fire. Case sets form_5472_present=false (bool) but the rule requires value: \"False\" (string). Type gotcha.",
      "flags": ["false-string-vs-bool-gotcha"]
    }
  ],

  "coverage_gaps": [],
  "warnings": [],

  "delta_from_last_run": {
    "last_run_id": "2026-04-09T18-00-00Z",
    "new_failures": ["A-entity-missing_5472-pos"],
    "new_passes": [],
    "new_unrunnable": [],
    "rules_with_score_change": ["missing_5472"],
    "unchanged_cases": 181
  },

  "telemetry": {
    "generator_calls": 7,
    "generator_calls_cached": 135,
    "judge_calls": 23,
    "judge_calls_cached": 159,
    "tokens_in_total": 14200,
    "tokens_out_total": 41700,
    "note": "codex CLI usage is subscription-billed; token counts are for prompt-tuning only"
  }
}
```

#### Markdown shape (abridged)

```markdown
# Rubric Loop — 2026-04-10 14:22 UTC

**Totals:** 167 pass / 11 partial / 3 fail / 1 unrunnable   (182 cases)
**Engine:** v1.0.0   **Rubric:** v0.1.0   **Model:** gpt-5.4 (xhigh)

## Delta from last run (2026-04-09 18:00)
- NEW FAIL: `A-entity-missing_5472-pos` — form_5472_present type gotcha
- unchanged: 181

## By track
| track         | cases | pass | partial | fail | unrunnable |
|---------------|------:|-----:|--------:|-----:|-----------:|
| stem_opt      |    46 |   44 |       2 |    0 |          0 |
| ...                                                          |

## By slice (A=pos, B=neg-near-miss, C=operator, D=categorization, E=edge)
| ...

## By dimension (weighted mean)
| categorization    |  0.97 |
| findings          |  0.91 |
| rule_quality      |  0.88 |
| operator_behavior |  1.00 |

## Failures
### A-entity-missing_5472-pos (fail)
- **Hard-fail:** positive_case_fires_target_rule scored 0.0
- **Judge note:** Rule `missing_5472` did not fire. Case sets `form_5472_present=false` (bool) but rule requires `value: "False"` (string).
- **Flags:** `false-string-vs-bool-gotcha`
- **Fixture:** `scripts/rubric_fixtures/A-entity-missing_5472-pos.json`

## Coverage gaps
None.

## Warnings
None.
```

Delta-from-last-run is the top section because iteration is the main use case — the user's primary question on run 2+ is "did my change help or hurt?"

## Codex Invocation Contract

### Baseline command

```bash
codex exec \
    -c "model_reasoning_effort=\"xhigh\"" \
    --model gpt-5.4 \
    --sandbox read-only \
    --skip-git-repo-check \
    --ephemeral \
    --output-schema scripts/rubric/schemas/<kind>-output.schema.json \
    --output-last-message <tmp-output-file> \
    --json \
    --cd /tmp/rubric-loop-workspace \
    - <<< "$PROMPT_TEXT"
```

### Flag rationale

| Flag | Why |
|---|---|
| `-c model_reasoning_effort="xhigh"` | Extra-high reasoning (house convention from `scripts/codex_loop/`) |
| `--model gpt-5.4` | General-purpose model (not `gpt-5.3-codex` — this is not a coding task) |
| `--sandbox read-only` | Prevents agent from writing files or running shell commands. Pure LLM call. |
| `--skip-git-repo-check` | Allows running from scratch workspace, not from the Guardian repo |
| `--ephemeral` | Don't persist session files to `~/.codex/sessions/` |
| `--output-schema` | Constrains final response to JSON Schema. Generator and judge each have their own schema. |
| `--output-last-message` | Writes clean final message to a file for easy parsing |
| `--json` | Stdout becomes JSONL events — parsed for token counts and latency |
| `--cd /tmp/rubric-loop-workspace` | Hermetic scratch directory; model has no access to Guardian repo |
| `-` + heredoc stdin | Avoids shell-escaping issues for multi-KB prompts |

**Key property:** the model can't cheat by reading `rule_engine.py` or the YAMLs. All rule knowledge is passed through the prompt text. The generator gets the rule snapshot + field reference table; the judge gets the case + engine findings + filtered criteria.

### Python wrapper — `scripts/rubric/codex_client.py`

```python
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

SCRATCH_WORKSPACE = Path("/tmp/rubric-loop-workspace")

# Defaults match user preference: general-purpose model for non-coding task
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_FALLBACK_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "xhigh"

MODEL = os.environ.get("RUBRIC_CODEX_MODEL", DEFAULT_MODEL)
FALLBACK_MODEL = os.environ.get("RUBRIC_CODEX_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
REASONING_EFFORT = os.environ.get("RUBRIC_CODEX_REASONING", DEFAULT_REASONING_EFFORT)


@dataclass
class CodexCallResult:
    text: str
    parsed: dict
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int
    raw_events: list[dict] = field(default_factory=list)
    attempts: int = 1


class CodexCallError(Exception):
    def __init__(self, kind: str, message: str, stderr: str = "", attempts: int = 1):
        super().__init__(message)
        self.kind = kind  # "timeout" | "schema_violation" | "subprocess_failure" | "parse_failure"
        self.message = message
        self.stderr = stderr
        self.attempts = attempts


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
    """Invoke `codex exec` with structured output, retries, telemetry, and fallback.

    Retries only on retryable kinds (timeout, parse_failure, schema_violation).
    Subprocess failures fail fast, except for "model is not supported" which
    triggers a one-shot fallback to `fallback_model`.
    """
    SCRATCH_WORKSPACE.mkdir(parents=True, exist_ok=True)
    last_error: CodexCallError | None = None

    for attempt in range(1, max_retries + 2):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as output_file:
            output_path = Path(output_file.name)

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
                cmd, input=prompt, text=True,
                capture_output=True, timeout=timeout_s,
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
            # One-shot fallback on unsupported-model errors,
            # matching scripts/codex_loop/run_batch_iteration.sh:141
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

        # Belt-and-suspenders local schema validation
        from jsonschema import Draft202012Validator, ValidationError
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
            for line in proc.stdout.splitlines()
            if line.strip()
        ]
        tokens_in, tokens_out = _extract_token_counts(events)

        return CodexCallResult(
            text=raw,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=_extract_latency_ms(events),
            raw_events=events,
            attempts=attempt,
        )

    assert last_error is not None
    raise last_error
```

**Properties worth preserving in implementation:**
- Double schema validation (codex enforces, we re-validate locally with `jsonschema`)
- Retries only retryable kinds (timeouts, parse, schema)
- Subprocess failures fail fast unless the output contains "model is not supported"
- Fallback is one-shot, non-recursive
- Token accounting from JSONL events; failure to parse events is soft (returns None)
- No global state; every call is hermetic

### Retry policy

| Attempt | Timeout | Parse/schema failure | Subprocess failure |
|---|---|---|---|
| 1 → 2 | wait 2s, retry | wait 0s, retry | fail fast (+ one-shot fallback on "model is not supported") |
| 2 → 3 | wait 5s, retry | wait 0s, retry | fail fast |
| 3 → FAIL | raise `CodexCallError` (case marked unrunnable, run continues) | raise | — |

### Output schemas

#### `scripts/rubric/schemas/generator-output.schema.json`

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

#### `scripts/rubric/schemas/judge-output.schema.json`

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
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "criteria_applied": {"type": "array", "items": {"type": "string"}},
            "note": {"type": "string"}
          }
        }
      },
      "additionalProperties": false
    },
    "flags": {"type": "array", "items": {"type": "string"}}
  }
}
```

Bumping `rubric_version.txt` is tied to editing `criteria.yaml` and/or these schemas. Version change invalidates judge cache but not fixtures or eval cache.

### Generator prompt template — `scripts/rubric/prompts/generator.md`

```markdown
# System

You are generating a single synthetic test case for a deterministic
compliance rule engine. The engine evaluates an EvaluationContext object
against a YAML-defined rule set and produces findings.

Your job is to produce the case input, not to evaluate or judge it.

Your output MUST conform to the JSON schema provided via --output-schema.
Produce JSON only. Do NOT emit markdown code fences, prose, or commentary.

Do not use real PII or real-looking government identifiers (SSNs,
A-numbers, receipt numbers, passport numbers). All names, employers,
schools, and identifiers must be fictional. You may use plain, realistic,
or playful framing — pick whichever makes the case clearest. Do not force
humor where it obscures the probe.

Do not attempt to read files, run shell commands, or use tools. Respond
with the final JSON only.

# User

## Target rule
```yaml
{rule_yaml_snapshot}
```

## Probe intent
{probe_intent}

## Case constraints
- case_id: {case_id}
- slice: {slice}                  (A=positive, B=negative near-miss)
- track: {track}
- target_rule_id: {target_rule_id}

## Field reference
These are the ONLY fields the engine can read. Any other fields you set
will be ignored:

{field_reference_table}

## Derivation reminders
- `is_nra` is derived automatically in rule_engine._derive_nra; do not
  set it directly. Set `tax_residency_status` (explicit) OR `stage` +
  `years_in_us` (heuristic) OR `owner_residency` (entity track).
- F-1 exempt stages: f1_student, opt, stem_opt. Years < 6 → is_nra=yes.
- h1b / i140 → is_nra=no.

## Value-type gotchas to respect
- `form_5472_present` must be the STRING "False" or "True", not a bool.
- `schedules_present` is a LIST of strings, e.g. ["schedule_c"].
- All dates must be YYYY-MM-DD ISO format.

## Your output
Produce a JSON object satisfying the output schema. The `input` object
maps 1:1 to rule_engine.EvaluationContext. The `expected` object states
what the engine should do.

For slice A: expected.must_fire_rule_ids MUST include "{target_rule_id}".
For slice B: expected.must_not_fire_rule_ids MUST include "{target_rule_id}",
    and the case must be adversarially close — something a naive reader
    would think SHOULD fire the rule.
```

### Judge prompt template — `scripts/rubric/prompts/judge.md`

```markdown
# System

You are grading the behavior of a deterministic compliance rule engine
on a single test case. You are NOT grading the case itself; you are
grading whether the engine did the right thing given the case.

Apply only the criteria provided. Do not invent additional criteria.
Do not speculate about rules or engine behavior not described here.

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
- If engine_error is present and the case did not expect an error,
  verdict is "unrunnable".

## Your output
JSON object with:
- `verdict`: "pass" | "partial" | "fail" | "unrunnable"
- `subscores`: per dimension, each with score, criteria_applied, note
- `flags`: optional list of free-form strings

Each dimension's `note` must cite specific facts from the case + findings
— e.g., "is_nra=yes because stage=stem_opt, years=3 (branch 2)." Vague
notes like "looks correct" are not acceptable.
```

## Error Handling

### Error taxonomy

| Class | Examples | Response |
|---|---|---|
| **Global** | `codex` not on PATH, malformed rule YAML, rubric schema unparseable, `CoverageGap`, output dir not writable | Abort run. Exit 2. No scorecard. Error points at offending file. |
| **Per-case** | Codex timeout after retries, schema violation after retries, unexpected engine exception, judge output unparseable | Mark case `unrunnable`, capture error, continue. Run produces scorecard; unrunnable is a first-class total. |
| **Warning** | Rule YAML hash changed but no cases re-evaluated, PII-shaped string in generated fixture, cross-rule contradictions detected | Log to stderr, include in scorecard `warnings`, do not fail. |

### Phase-specific handling

- **Phase 0** — all errors global. CoverageGap aborts before any codex call.
- **Phase 1** — per-case. Codex errors write a sentinel fixture (`"unrunnable": true` + `last_error`) so subsequent runs don't blindly retry. Explicit `--regen` required. PII regex check runs on every generated fixture (matches SSN-like, A-number-like, receipt-number-like strings → warning, not failure).
- **Phase 2** — per-case. Engine exceptions captured in `engine_error`. Slice-C cases can expect errors; others are unrunnable.
- **Phase 3** — per-case. Judge parse failures → unrunnable with raw output preserved.
- **Phase 4** — global. Corrupt cache aborts; manual `rm -rf scripts/rubric_cache/` is the fix.

### `--fail-fast` opt-in

Flips per-case errors to global errors. Used when iterating on generator prompts and wanting to see the first broken output immediately.

## Testing the Harness

Four test layers at `tests/test_rubric_loop.py`:

**Layer 1 — Unit tests** (pure, no codex, no engine):
- `discover.py` — feed hand-built YAMLs, verify manifest has exactly expected case IDs. Test that adding a rule grows manifest by 2. Test that missing rule → `CoverageGap`.
- `case_ids.py` — fuzz over rule IDs, verify no collisions, verify round-trip.
- `aggregate.py` — hand-built subscore dicts → verify verdict thresholds, hard-fail logic, dimension weighting.

**Layer 2 — Codex wrapper tests** (monkeypatched subprocess):
- `codex_client.py` — cover success, timeout, parse failure retry, schema violation, `"model is not supported"` fallback, subprocess failure fast-fail. **No actual codex calls in the test suite.**

**Layer 3 — Engine integration tests** (real engine, mocked codex):
- Hand-write a fixture, run Phase 2, verify eval cache writes correct findings.
- Poison fixture (malformed `answers`) → verify `engine_error` captured, case `unrunnable`.

**Layer 4 — End-to-end smoke test** (real codex, opt-in, slow):
- Marked `@pytest.mark.slow`, gated behind `RUBRIC_E2E=1` env var. One real codex call end-to-end to catch schema/prompt regressions.

### Meta-test: "deliberately broken rule"

`tests/fixtures/broken_rules.yaml` contains a rule with contradictory conditions (e.g., `stage eq f1_student` AND `stage eq h1b`). The meta-test runs the full loop against this file and asserts:
- (a) Phase 0 does not crash
- (b) Phase 1 generates a slice-A case (generator doesn't know it's broken)
- (c) Phase 2 evaluates to no findings for that rule
- (d) Phase 3 flags `positive_case_fires_target_rule` as hard-fail
- (e) Scorecard marks this case fail
- (f) Judge note mentions the rule didn't fire

**If this test ever passes without flagging the broken rule, the rubric loop is silently broken.** This is the highest-value test in the suite.

## Reproducibility and Logging

**Reproducibility invariant:** given identical fixtures + rule YAMLs + rubric criteria + engine version, the scorecard is byte-identical across runs on the same machine. Codex output is non-deterministic, which is why we cache — on a cache hit, the judgment is frozen.

Anyone pulling the repo and running `python scripts/rubric_loop.py --phases evaluate,judge,aggregate` against committed fixtures should see the same scorecard the author saw.

**Scorecard pins down:** `engine_version`, `rubric_version`, `codex_version`, `codex_model`, `reasoning_effort`. If any changes between runs, the scorecard diff tells you which axis moved.

**Logging:**
- Default `INFO`. Each phase prints a banner: `Phase 1/4: Generate-missing — 3 new, 139 cached, 0 errors`
- `-v` / `--verbose`: `DEBUG`. Prints each codex call's model, prompt hash, outcome, latency.
- `-q` / `--quiet`: `WARNING` and above. Useful when piping scorecard JSON to `jq`.
- Logs → stderr. Scorecard JSON → `out/` (or stdout with `--json-stdout`). Markdown scorecard → `out/`.

## Flag Semantics at the Edges

| Scenario | Behavior |
|---|---|
| `--only <rule_id>` with no matching cases | Exit 2 with error. Never silently runs zero cases. |
| `--only <rule_id> --slice B` | Runs slice-B negative case for that rule only. Empty intersection → exit 2. |
| `--regen` no arg | Regenerates all slice-A+B fixtures. Goldens untouched. Clears eval+judge cache for regenerated cases. |
| `--regen A` | Regenerates slice-A only. |
| `--regen C` | **Error** — can't regenerate static goldens. Suggests editing `rubric_fixtures/goldens/*.json` directly. |
| `--phases discover,aggregate` | Skips generate/evaluate/judge. Aggregator reads cache. Empty cache → exit 2. |
| `--phases generate` | Only Phase 1. No scorecard. Pre-populate cache. |
| `--no-gen` | Alias for `discover,evaluate,judge,aggregate`. Most common daily-iteration flag. |
| `--no-judge` | Alias for `discover,generate,evaluate,aggregate`. Engine output without verdicts. |
| `--fail-fast` | First per-case error aborts. No scorecard. Exit 1. |
| `--only` + `--no-gen` + missing fixture | Exit 2 with "fixture missing for case X; use --regen or drop --no-gen." |
| `--regen` + `--phases evaluate,judge` | Contradictory. Exit 2. |

**Invariant:** every flag combination either does something unambiguous or fails fast. No silent no-ops.

## Implementation Sequencing

This section is a hint for the implementation plan (written separately after this spec is approved). The build order that minimizes integration risk:

1. **Discovery + case enumeration** — write `discover.py` and `case_ids.py`, hand-write a few slice-A case specs in tests, verify manifest shape. No codex, no engine.
2. **Goldens directory scaffold** — hand-write 3-5 golden fixtures (one slice-C operator stress, one slice-D NRA branch, one slice-E edge case). This proves the golden loader before spending time on LLM generation.
3. **Engine integration** — `evaluate.py` + eval cache. Feed in the goldens from step 2, verify engine runs produce expected output. No codex.
4. **Codex wrapper** — `codex_client.py` with mocked subprocess tests. No actual codex calls yet.
5. **Generator** — `generate.py` + `prompts/generator.md` + `schemas/generator-output.schema.json`. First real codex calls. Smoke test with one slice-A case.
6. **Judge** — `judge.py` + `prompts/judge.md` + `schemas/judge-output.schema.json` + `config/rubric/criteria.yaml`. Second set of real codex calls.
7. **Aggregation + scorecard** — `aggregate.py`. Assemble the scorecard from cached artifacts.
8. **Main entrypoint** — `rubric_loop.py` wiring everything together + argparse + flag handling.
9. **Meta-test** — the "deliberately broken rule" test.
10. **Remaining static goldens** — fill out the slice-C/D/E set to ~40 cases.
11. **First full run** — ship slice-A + slice-B fixture generation; verify end-to-end; check scorecard.
12. **Commit fixtures** — review the ~142 generated fixtures, commit to git.

Steps 1-4 have no external dependencies and can be TDD'd aggressively. Steps 5-6 are where codex integration begins and where most debugging time will go. Step 11 is the first moment the scorecard has real signal.

## Follow-ups and Open Questions

Parked for later, not blocking v0:

- **CI integration.** `--phases evaluate,judge,aggregate --fail-fast` is CI-ready but no workflow file is written in v0.
- **Parallel workers.** If sequential full runs become painful (>15 min), revisit Architecture 3 (rule-parallel fan-out).
- **Fixture review tooling.** A small script that renders a fixture JSON as a human-readable markdown summary would help code review — out of scope for v0, easy follow-up.
- **Rubric criteria expansion.** The 11 criteria in v0 are first-draft. Expect to add more as real failure modes surface.
- **Cost tracking for non-codex LLM calls.** If any future phase of the loop uses direct API calls instead of codex CLI, re-introduce cost tracking for those specific calls.

## Appendix: The 52-field inventory

Every field the engine can read (grep'd from `config/rules/*.yaml`):

```
1042s_tax_return_tax_year            has_multistate_health
compensation                          i9_everify_employee_name
cpt_application_i20_student_name      i9_everify_first_day_of_employment
cpt_fulltime_months                   i94_i20_class_of_admission
duties                                income_reporting
employer_changed                      is_nra
employer_name                         job_title
employment_letter_i9_employee_name    missing_registration_packet
employment_letter_paystub_employer_name  owner_residency
employment_status                     passport_ead_date_of_birth
end_date                              pending_status_change
entity_type                           petition_status
filed_8843                            petition_window_closed
foreign_capital_transfer              planning_travel
form_5472_present                     received_foreign_gifts
form_type                             registration_number
formation_age                         resume_passport_candidate_name
full_time                             schedules_present
h1b_invoice_receipt_amount            separate_bank_account
h1b_registration_g28_entity_name      stage
h1b_registration_invoice_petitioner_name  start_date
h1b_registration_receipt_signatory_name  tax_software_used
has_cpt_authorization                 visa_type
has_employment                        w2_tax_return_tax_year
has_foreign_accounts                  work_location
has_govt_health_plan                  years_in_us
```

Plus four derivation inputs read by `_derive_nra` not all directly referenced in rule conditions: `tax_residency_status` (others are already in the list). Generator's field reference table includes all of these.
