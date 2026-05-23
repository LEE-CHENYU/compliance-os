"""User-facts SoT layer — the canonical-vocabulary side of Guardian's
context-management policy. See docs/architecture/context-management.md
for the full design.
"""

from compliance_os.facts.vocabulary import (
    CANONICAL_FACTS,
    FactDef,
    canonical_keys_for_track,
    is_canonical_key,
    resolve_fact_def,
)

__all__ = [
    "CANONICAL_FACTS",
    "FactDef",
    "canonical_keys_for_track",
    "is_canonical_key",
    "resolve_fact_def",
]
