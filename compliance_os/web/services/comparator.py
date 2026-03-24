"""Field comparison engine — exact, fuzzy, numeric, semantic."""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz


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
