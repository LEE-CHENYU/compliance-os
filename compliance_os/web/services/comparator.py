"""Field comparison engine — exact, fuzzy, entity, numeric."""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz


# Legal entity suffixes that imply a specific entity type. A different
# suffix signals a different legal entity even if the base name matches.
# We match after punctuation is stripped so "L.L.C." and "LLC" normalize alike.
_ENTITY_SUFFIX_PATTERN = re.compile(
    r"\b(inc|incorporated|llc|corp|corporation|co|company|ltd|limited|lp|llp|pllc|plc|gmbh|sa|ag|pty|pte)\b",
    re.IGNORECASE,
)
# Collapse sequences like "L.L.C." or "L.P." (letter-period initials) into
# letter-only form "LLC" / "LP". Run before _PUNCT_PATTERN so the resulting
# token stays glued.
_DOTTED_INITIALS_PATTERN = re.compile(r"(?:\b[A-Za-z]\.){2,}")
_PUNCT_PATTERN = re.compile(r"[.,;]+")


def _collapse_dotted_initials(text: str) -> str:
    return _DOTTED_INITIALS_PATTERN.sub(lambda m: m.group(0).replace(".", ""), text)
# Map variants → canonical suffix so "Ltd"/"Limited", "Inc"/"Incorporated",
# "Corp"/"Corporation", "Co"/"Company" are treated as the same entity type.
_SUFFIX_CANONICAL: dict[str, str] = {
    "incorporated": "inc",
    "corporation": "corp",
    "company": "co",
    "limited": "ltd",
}


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


def _normalize_for_entity(text: str) -> str:
    """Lowercase, collapse dotted initials (L.L.C. → LLC), drop punctuation, collapse whitespace."""
    collapsed = _collapse_dotted_initials(text.lower())
    return " ".join(_PUNCT_PATTERN.sub(" ", collapsed).split())


def _entity_suffix(text: str) -> str | None:
    """Return the canonical entity suffix if any, else None."""
    normalized = _normalize_for_entity(text)
    match = _ENTITY_SUFFIX_PATTERN.search(normalized)
    if not match:
        return None
    raw = match.group(1).lower()
    return _SUFFIX_CANONICAL.get(raw, raw)


def _strip_entity_suffix(text: str) -> str:
    normalized = _normalize_for_entity(text)
    stripped = _ENTITY_SUFFIX_PATTERN.sub("", normalized)
    return " ".join(stripped.split())


def _entity(name: str, a: str, b: str) -> ComparisonResult:
    """Compare legal entity names. Flag suffix mismatches (Inc vs LLC) as mismatches."""
    suffix_a = _entity_suffix(a)
    suffix_b = _entity_suffix(b)
    base_a = _strip_entity_suffix(a)
    base_b = _strip_entity_suffix(b)
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
