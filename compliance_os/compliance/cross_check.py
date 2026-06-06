"""Chain-aware local compliance cross-check.

Reads the on-device facts SoT + each document's extracted fields and reports
cross-document fact mismatches, missing-from-chain documents, and deadline
risks. Deterministic and local — no model call, no network. Chain knowledge
lives in config/document_chains.yaml; this module is chain-agnostic.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parents[2] / "config" / "document_chains.yaml"


@lru_cache(maxsize=1)
def load_chains() -> dict:
    """Load the chain spec. Cached; call load_chains.cache_clear() in tests
    that write a custom config."""
    with open(_CONFIG) as f:
        return (yaml.safe_load(f) or {}).get("chains", {})


def _contributions(db, user_id: str) -> dict:
    """Map every active document's extracted fields to canonical fact keys.

    Returns {fact_key: [(doc_type, doc_id, value), ...]} — each document's raw
    contribution to each canonical key (via EXTRACTION_TO_FACT_KEY), preserving
    provenance so mismatches can cite their sources.
    """
    from compliance_os.facts.extraction_map import fact_key_for
    from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow

    docs = (
        db.query(DocumentRow)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id, DocumentRow.is_active.is_(True))
        .all()
    )
    out: dict = {}
    for doc in docs:
        for ef in doc.extracted_fields:
            if not ef.field_value:
                continue
            fk = fact_key_for(doc.doc_type, ef.field_name)
            if fk is None:
                continue
            out.setdefault(fk, []).append((doc.doc_type, doc.id, ef.field_value))
    return out


def _present_doc_types(db, user_id: str) -> set:
    from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow

    rows = (
        db.query(DocumentRow.doc_type)
        .join(CheckRow, CheckRow.id == DocumentRow.check_id)
        .filter(CheckRow.user_id == user_id, DocumentRow.is_active.is_(True))
        .all()
    )
    return {r[0] for r in rows}
