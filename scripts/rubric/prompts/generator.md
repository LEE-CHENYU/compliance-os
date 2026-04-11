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
