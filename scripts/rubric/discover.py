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
