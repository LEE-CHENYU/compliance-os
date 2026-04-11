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

Produce a JSON object with EXACTLY this top-level shape. Copy the structure below — do not flatten, do not rename keys, do not add top-level keys.

```json
{
  "input": {
    "answers": {},
    "extraction_a": {},
    "extraction_b": {},
    "comparisons": {}
  },
  "expected": {
    "must_fire_rule_ids": [],
    "must_not_fire_rule_ids": [],
    "expected_nra": "yes",
    "expected_track": "stem_opt",
    "notes": ""
  },
  "flavor_hint": null
}
```

**Critical shape rules:**
- `input` has EXACTLY 4 sub-keys: `answers`, `extraction_a`, `extraction_b`, `comparisons`. All 4 must be present (use `{}` if nothing goes in them). `comparisons` is plural with an 's'.
- Put user-entered answers under `input.answers` (stage, years_in_us, employment_status, employer_changed, etc.).
- Put document-extracted fields under `input.extraction_a` (typically doc A: I-983, I-20, tax return body) or `input.extraction_b` (typically doc B: employment letter, employer name).
- Put cross-document comparison results under `input.comparisons` as `{"field_name": {"status": "mismatch"|"match"|"needs_review", "confidence": 0.0-1.0}}`.
- `expected` has EXACTLY 5 sub-keys: `must_fire_rule_ids`, `must_not_fire_rule_ids`, `expected_nra`, `expected_track`, `notes`. All must be present. `expected_nra` is `"yes"` or `"no"` (compute using the derivation reminders above). `expected_track` is the same as the track constraint. `notes` is a one-sentence explanation.
- `flavor_hint` is `null` by default.

## Example for a comparison rule

For `job_title_mismatch` (slice A, positive — engine MUST fire), a valid output is:

```json
{
  "input": {
    "answers": {"stage": "stem_opt", "years_in_us": 3, "employer_changed": "no"},
    "extraction_a": {"job_title": "Senior Platform Engineer", "start_date": "2024-06-15", "end_date": "2027-06-14"},
    "extraction_b": {"job_title": "Staff Engineer"},
    "comparisons": {"job_title": {"status": "mismatch", "confidence": 0.92}}
  },
  "expected": {
    "must_fire_rule_ids": ["job_title_mismatch"],
    "must_not_fire_rule_ids": [],
    "expected_nra": "yes",
    "expected_track": "stem_opt",
    "notes": "I-983 and employment letter disagree on job title; engine should fire job_title_mismatch. is_nra=yes from branch 2 (stem_opt + years<6)."
  },
  "flavor_hint": null
}
```

## Slice-specific requirements

For slice A: expected.must_fire_rule_ids MUST include "{target_rule_id}".
For slice B: expected.must_not_fire_rule_ids MUST include "{target_rule_id}", and the case must be adversarially close — something a naive reader would think SHOULD fire the rule. Satisfy MOST of the rule's conditions but break exactly ONE.
