"""Match a professional-search to relevant Guardian marketplace products.

When a user runs an open-world lawyer search, some of those needs map
cleanly to Guardian's own paid products (Form 8843, OPT advisory,
H-1B doc check, FBAR, 83(b)). This module produces a small ranked list
of "we can do this for you directly" recommendations to surface above
the external-firm tier report.

Two-stage match:
  1. **Vertical filter** — only products whose category matches the
     search vertical's domain are considered.
  2. **Brief refinement** — case_brief is keyword-scanned to bump
     specific products. A brief that mentions "FBAR" should put
     fbar_check at the top of a tax search even if other tax products
     would also qualify.

Determinstic and self-contained — no LLM call. The matcher returns
fewer products when nothing fits (often zero, e.g. for EB-5 / banks /
CAA verticals where Guardian has no equivalent product).
"""
from __future__ import annotations

import re
from typing import Any

from compliance_os.web.services.product_catalog import (
    list_product_configs,
    serialize_product,
)


# Coarse map: search vertical → product category. A vertical may map
# to multiple categories (a generic immigration search can also reach
# the startup-categorized 83(b) product if the brief asks for it).
_VERTICAL_CATEGORIES: dict[str, list[str]] = {
    "immigration_attorney": ["immigration"],
    "immigration_h1b": ["immigration"],
    "immigration_o1_niw": [],  # No Guardian product for O-1/NIW yet; no generic H-1B upsell.
    "immigration_eb5": [],  # No Guardian product for EB-5; no upsell.
    "tax_attorney": ["tax"],
    "cpa": ["tax"],
    "corporate_attorney": ["startup"],
    "bank": [],
    "caa": ["tax"],  # CAAs handle ITIN; closest Guardian product is tax filing.
}

# Brief keyword → SKU score boost. Matched case-insensitively as whole
# words/phrases; the higher-scoring SKUs surface first.
_KEYWORD_BOOSTS: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(r"\bopt\b|\boptional practical training\b", re.I), "opt_advisory", 30),
    (re.compile(r"\bopt\b|\boptional practical training\b", re.I), "opt_execution", 25),
    (re.compile(r"\bh-?1b\b", re.I), "h1b_doc_check", 30),
    (re.compile(r"\bfbar\b|\bfbinen\b|\bforeign account\b|\bfincen 114\b", re.I), "fbar_check", 35),
    (re.compile(r"\b83\s*\(?b\)?\b|\bsection 83\(b\)\b|\bstock options?\b|\brsus?\b|\bequity grant\b", re.I), "election_83b", 35),
    (re.compile(r"\b1040-?nr\b|\bstudent tax\b|\bf-?1 student\b|\bj-?1 student\b", re.I), "student_tax_1040nr", 30),
    (re.compile(r"\bform 8843\b|\b8843\b|\bsubstantial presence\b", re.I), "form_8843_free", 25),
]

# Floor for a vertical-default match — every active product in a matched
# category gets at least this score so it shows up even with no keywords.
_DEFAULT_SCORE = 10

# Cap how many recommendations we render. The page already has a tier
# report and a paywall; the upsell should be tight, not a second catalog.
MAX_RECOMMENDATIONS = 2


def _match_keyword_boosts(brief: str) -> dict[str, int]:
    boosts: dict[str, int] = {}
    if not brief:
        return boosts
    for pattern, sku, score in _KEYWORD_BOOSTS:
        if pattern.search(brief):
            # Take the strongest hit per SKU — duplicate hints don't compound.
            boosts[sku] = max(boosts.get(sku, 0), score)
    return boosts


def match_products(
    *, vertical: str, case_brief: str | None = None
) -> list[dict[str, Any]]:
    """Return up to MAX_RECOMMENDATIONS matched products for this search.

    Each entry is the product config dict (from product_catalog) plus:
      - `match_score`: int (higher = stronger match)
      - `match_reason`: human-readable string ("matches your case mention of OPT")
    """
    categories = _VERTICAL_CATEGORIES.get(vertical, [])
    if not categories:
        return []

    products = list_product_configs(include_inactive=False)
    boosts = _match_keyword_boosts(case_brief or "")

    matches: list[tuple[int, str, dict[str, Any]]] = []
    for product in products:
        category = str(product.get("category") or "")
        if category not in categories:
            continue
        sku = str(product["sku"])
        score = _DEFAULT_SCORE
        keyword_boost = boosts.get(sku, 0)
        score += keyword_boost
        reason = (
            f"Matches your mention of {_keyword_label_for(sku)}"
            if keyword_boost
            else f"Common Guardian service for {vertical.replace('_', ' ')} cases"
        )
        matches.append((score, sku, {
            **serialize_product(product),
            "match_score": score,
            "match_reason": reason,
        }))

    # Highest score first, deterministic tiebreaker on SKU so output is
    # stable across runs (prevents UI flicker on re-renders).
    matches.sort(key=lambda m: (-m[0], m[1]))
    return [m[2] for m in matches[:MAX_RECOMMENDATIONS]]


def _keyword_label_for(sku: str) -> str:
    """Human-readable label for the keyword that matched a SKU."""
    return {
        "opt_advisory": "OPT",
        "opt_execution": "OPT",
        "h1b_doc_check": "H-1B",
        "fbar_check": "FBAR / foreign accounts",
        "election_83b": "83(b) / equity grants",
        "student_tax_1040nr": "1040-NR / student tax",
        "form_8843_free": "Form 8843",
    }.get(sku, "your specific situation")
