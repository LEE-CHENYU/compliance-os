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
