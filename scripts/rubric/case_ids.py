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
