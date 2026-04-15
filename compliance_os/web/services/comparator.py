"""Field comparison engine — exact, fuzzy, entity, numeric."""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz


# Legal entity suffixes that imply a specific entity type. A different
# suffix signals a different legal entity even if the base name matches.
_ENTITY_SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c\.|corp|corporation|co|company|ltd|limited|lp|l\.p\.|llp|l\.l\.p\.|pllc|plc|gmbh|sa|ag|pty|pte)\b",
    re.IGNORECASE,
)
_PUNCT_PATTERN = re.compile(r"[.,;]+")


@dataclass
class ComparisonResult:
    field_name: str
    value_a: str | None
    value_b: str | None
    match_type: str
    status: str  # match | mismatch | needs_review
    confidence: float
    detail: str | None = None


def compare_fields(
    field_name: str,
    value_a: str | None,
    value_b: str | None,
    match_type: str,
) -> ComparisonResult:
    if value_a is None or value_b is None:
        return ComparisonResult(
            field_name, value_a, value_b, match_type, "needs_review", 0.0,
            "One or both values missing",
        )

    a = str(value_a).strip()
    b = str(value_b).strip()

    if match_type == "exact":
        return _exact(field_name, a, b)
    if match_type == "fuzzy":
        return _fuzzy(field_name, a, b)
    if match_type == "entity":
        return _entity(field_name, a, b)
    if match_type == "numeric":
        return _numeric(field_name, a, b)
    return ComparisonResult(
        field_name, a, b, match_type, "needs_review", 0.0,
        f"Unknown match type: {match_type}",
    )


def _exact(name: str, a: str, b: str) -> ComparisonResult:
    match = a.lower() == b.lower()
    return ComparisonResult(name, a, b, "exact", "match" if match else "mismatch", 1.0 if match else 0.0)


def _fuzzy(name: str, a: str, b: str) -> ComparisonResult:
    ratio = fuzz.token_sort_ratio(a.lower(), b.lower()) / 100.0
    status = "match" if ratio >= 0.85 else "mismatch"
    return ComparisonResult(name, a, b, "fuzzy", status, ratio)


def _entity_suffix(text: str) -> str | None:
    """Return the normalized entity suffix if any, else None."""
    match = _ENTITY_SUFFIX_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).lower().replace(".", "")


def _strip_entity_suffix(text: str) -> str:
    stripped = _ENTITY_SUFFIX_PATTERN.sub("", text)
    stripped = _PUNCT_PATTERN.sub("", stripped)
    return " ".join(stripped.split())


def _entity(name: str, a: str, b: str) -> ComparisonResult:
    """Compare legal entity names. Flag suffix mismatches (Inc vs LLC) as mismatches."""
    suffix_a = _entity_suffix(a)
    suffix_b = _entity_suffix(b)
    base_a = _strip_entity_suffix(a).lower()
    base_b = _strip_entity_suffix(b).lower()
    base_ratio = fuzz.token_sort_ratio(base_a, base_b) / 100.0

    if suffix_a and suffix_b and suffix_a != suffix_b:
        return ComparisonResult(
            name, a, b, "entity", "mismatch", base_ratio,
            f"Base names match ({base_ratio:.0%}) but entity types differ: {suffix_a} vs {suffix_b}",
        )

    status = "match" if base_ratio >= 0.92 else "mismatch"
    detail = None
    if status == "mismatch":
        detail = f"Base names differ ({base_ratio:.0%})"
    elif suffix_a != suffix_b:
        detail = f"Entity suffix present on only one side: {suffix_a or suffix_b}"
    return ComparisonResult(name, a, b, "entity", status, base_ratio, detail)


def _numeric(name: str, a: str, b: str) -> ComparisonResult:
    try:
        va = float(a.replace(",", "").replace("$", ""))
        vb = float(b.replace(",", "").replace("$", ""))
    except ValueError:
        return ComparisonResult(name, a, b, "numeric", "needs_review", 0.0, "Could not parse numbers")

    if va == 0 and vb == 0:
        return ComparisonResult(name, a, b, "numeric", "match", 1.0)

    max_val = max(abs(va), abs(vb))
    diff_pct = abs(va - vb) / max_val if max_val > 0 else 0
    within_tolerance = diff_pct <= 0.02 or abs(va - vb) <= 500
    confidence = max(1.0 - diff_pct, 0.0)
    return ComparisonResult(name, a, b, "numeric", "match" if within_tolerance else "mismatch", confidence)
