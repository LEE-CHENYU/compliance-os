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


import re

_DIGIT_KEYS = {"current_employer_ein", "entity_ein", "ssn_last4", "sevis_id",
               "i94_admission_number", "h1b_receipt_number"}
_MONEY_KEYS = {"current_annual_salary", "foreign_account_aggregate_high"}
_HIGH_SEVERITY = {"legal_name", "sevis_id", "current_employer_ein", "entity_ein",
                  "entity_legal_name", "current_employer_legal_name"}


def _normalize(fact_key: str, value: str) -> str:
    v = (value or "").strip()
    if fact_key in _DIGIT_KEYS:
        return re.sub(r"\D", "", v)
    if fact_key in _MONEY_KEYS:
        digits = re.sub(r"[^\d.]", "", v)
        try:
            return str(int(round(float(digits)))) if digits else ""
        except ValueError:
            return digits
    # names / addresses / titles: case-fold, collapse whitespace, drop common
    # corporate-suffix punctuation so "Acme Inc." == "Acme Inc" but "Acme Inc"
    # != "Acme Incorporated".
    v = re.sub(r"\s+", " ", v).strip().casefold().rstrip(".")
    return v


def _mismatches(keys, contributions) -> list:
    """For each key, if ≥2 distinct normalized values appear across its
    contributing documents, emit a mismatch finding citing every source."""
    findings = []
    for key in keys:
        items = contributions.get(key, [])
        groups: dict = {}
        for doc_type, doc_id, value in items:
            groups.setdefault(_normalize(key, value), []).append(
                {"value": value, "doc": doc_type, "doc_id": doc_id})
        groups.pop("", None)
        if len(groups) >= 2:
            findings.append({
                "category": "mismatch",
                "severity": "high" if key in _HIGH_SEVERITY else "medium",
                "fact": key,
                "values": [g[0] for g in groups.values()],  # one representative per distinct value
                "message": f"'{key}' differs across your documents — these should match.",
                "recommended_action": "Confirm the correct value and fix the document that's wrong.",
            })
    return findings


def _detect_chains(present_doc_types: set) -> list:
    chains = load_chains()
    return [cid for cid, c in chains.items()
            if any(dt in present_doc_types for dt in c.get("detect_when_any", []))]


def _missing(chain_id: str, present_doc_types: set) -> list:
    chain = load_chains()[chain_id]
    findings = []
    for d in chain.get("documents", []):
        if d.get("required") and d["doc_type"] not in present_doc_types:
            findings.append({
                "category": "missing",
                "severity": "high",
                "chain": chain_id,
                "doc_type": d["doc_type"],
                "label": d.get("label", d["doc_type"]),
                "message": f"{chain['name']}: required document missing — {d.get('label', d['doc_type'])}.",
                "recommended_action": f"Upload your {d.get('label', d['doc_type'])}.",
            })
    return findings
