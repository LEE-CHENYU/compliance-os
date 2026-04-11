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
    # Always document derived/gotcha fields (e.g. is_nra) even when absent from conditions
    for f in TYPE_GOTCHAS:
        fields.add(f)

    lines = ["| field | notes |", "|---|---|"]
    for f in sorted(fields):
        note = TYPE_GOTCHAS.get(f, "")
        lines.append(f"| `{f}` | {note} |")
    return "\n".join(lines)
