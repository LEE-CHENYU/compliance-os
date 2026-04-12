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
