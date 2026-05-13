"""Ingest search-agent YAML results into the diligence DB.

Each YAML document describes firms surfaced by one search persona (e.g.
elite_boutique, startup_founder, litigation_contrarian). Firms are
upserted into `vendors`; a contact, engagement, quotes, and evaluations
are created per firm. Optional `case_risks:` at the top level fans out
case-level risks to every engagement created or touched in the run.

Input schema (YAML)
-------------------
    agent: elite_boutique                 # free-form persona tag
    vertical: immigration_attorney        # controls vendor_type + category
    purpose: "H-1B petition — Yangtze Capital"  # engagement purpose (required)
    case_risks:                           # optional, applied to each engagement
      - risk: "Multi-registration concern"
        severity: critical
        mitigation: "Dissolve BSGC; 'entities not related' memo"
      - risk: "$100k H-1B proclamation exposure"
        severity: critical
        mitigation: "Continuous CPT bridge"
    firms:
      - name: "Maggio Kattar Nahajzer + Alexander, P.C."
        lead_attorney: "Andrew Nahajzer"
        role: "Partner"
        city: "Washington"
        state: "DC"
        phone: "(202) 483-0053"
        email: "info@maggio-kattar.com"
        website: "https://www.maggio-kattar.com"
        consultation_fee_low: null
        consultation_fee_high: null
        petition_fee_low: 5000
        petition_fee_high: 9000
        service_fee_label: "H-1B petition (estimated)"
        confidence: 70
        why_fit: "..."
        credentials: ["Chambers USA Immigration ranked", ...]
        risks: ["DC-based, remote only"]
        sources: ["https://..."]

Usage
-----
    from compliance_os.professional_search.ingest import ingest_docs
    summary = ingest_docs([Path("agent1.yaml"), Path("agent2.yaml")])
"""
from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path
from typing import Any

import yaml

from compliance_os.professional_search.db import (
    add_evaluation,
    add_quote,
    add_risk,
    connect,
    init_schema,
    upsert_contact,
    upsert_engagement,
    upsert_vendor,
)


VERTICAL_DEFAULTS: dict[str, dict[str, str]] = {
    "immigration_attorney": {"vendor_type": "attorney", "category": "immigration"},
    "immigration_h1b":      {"vendor_type": "attorney", "category": "immigration_h1b"},
    "immigration_o1_niw":   {"vendor_type": "attorney", "category": "immigration_o1_niw"},
    "immigration_eb5":      {"vendor_type": "attorney", "category": "immigration_eb5"},
    "tax_attorney":         {"vendor_type": "attorney", "category": "tax"},
    "corporate_attorney":   {"vendor_type": "attorney", "category": "corporate"},
    "cpa":                  {"vendor_type": "cpa",      "category": "tax"},
    "bank":                 {"vendor_type": "bank",     "category": "business_banking"},
    "caa":                  {"vendor_type": "caa",      "category": "itin"},
}


def _existing_vendor_id(conn: sqlite3.Connection, name: str) -> int | None:
    """Case-insensitive exact match, with a fuzzy fallback on the first word."""
    row = conn.execute(
        "SELECT id, name FROM vendors WHERE LOWER(name) = LOWER(?)", (name,),
    ).fetchone()
    if row:
        return row["id"]
    head = name.split()[0] if name.split() else ""
    if len(head) >= 4:
        row = conn.execute(
            "SELECT id, name FROM vendors WHERE name LIKE ?",
            (f"{head}%",),
        ).fetchone()
        if row:
            return row["id"]
    return None


def _confidence_to_priority(confidence: int | None) -> str:
    if confidence is None:
        return "low"
    if confidence >= 85:
        return "high"
    if confidence >= 70:
        return "medium"
    return "low"


def ingest_firm(
    conn: sqlite3.Connection,
    firm: dict,
    *,
    agent_tag: str,
    purpose: str,
    vendor_type: str,
    category: str,
    today_iso: str,
) -> tuple[int, int, bool]:
    """Insert/update one firm. Returns (vendor_id, engagement_id, was_new_vendor)."""
    name = firm["name"]
    was_new = _existing_vendor_id(conn, name) is None

    notes_parts: list[str] = []
    if firm.get("why_fit"):
        notes_parts.append(firm["why_fit"])
    notes_parts.append(f"[Surfaced by {agent_tag} search {today_iso}]")
    if firm.get("credentials"):
        notes_parts.append("Credentials: " + "; ".join(firm["credentials"]))
    if firm.get("risks"):
        notes_parts.append("Firm-level risks: " + "; ".join(firm["risks"]))
    notes = " | ".join(notes_parts)

    vid = upsert_vendor(
        conn,
        name=name,
        vendor_type=vendor_type,
        category=category,
        city=firm.get("city"),
        state=firm.get("state"),
        website=firm.get("website"),
        notes=notes,
    )

    if firm.get("lead_attorney") or firm.get("lead_contact"):
        upsert_contact(
            conn, vid,
            name=firm.get("lead_attorney") or firm["lead_contact"],
            role=firm.get("role"),
            email=firm.get("email"),
            phone=firm.get("phone"),
            is_primary=1,
        )

    eid = upsert_engagement(
        conn, vid,
        purpose=purpose,
        status="prospective",
        decision_rationale=firm.get("why_fit"),
        priority=_confidence_to_priority(firm.get("confidence")),
        score=firm.get("confidence"),
        next_action="Reach out for initial inquiry",
    )

    if firm.get("consultation_fee_low") is not None:
        low = firm["consultation_fee_low"]
        high = firm.get("consultation_fee_high") or low
        add_quote(
            conn, eid,
            service="Paid consultation",
            amount_low=low,
            amount_high=high,
            is_firm=1 if low == high else 0,
        )
    if firm.get("petition_fee_low") is not None:
        low = firm["petition_fee_low"]
        high = firm.get("petition_fee_high") or low
        add_quote(
            conn, eid,
            service=firm.get("service_fee_label", "Primary service (estimated)"),
            amount_low=low,
            amount_high=high,
            is_firm=0,
        )

    src_str = ", ".join(firm.get("sources") or [])[:200]
    for cred in firm.get("credentials") or []:
        add_evaluation(conn, eid, criterion="Credential", rating=cred, source=src_str)
    if firm.get("litigation_capability"):
        add_evaluation(
            conn, eid,
            criterion="Litigation capability",
            rating=firm["litigation_capability"],
        )
    if firm.get("confidence") is not None:
        add_evaluation(
            conn, eid,
            criterion="Search-agent confidence",
            rating=str(firm["confidence"]),
            source=agent_tag,
        )

    return vid, eid, was_new


def ingest_docs(paths: list[Path] | list[str]) -> dict[str, Any]:
    """Ingest one or more YAML docs. Returns a summary dict suitable for JSON.

    Each file must parse to a dict with at least `firms:`. Optional top-level
    keys:
        agent: persona name (default "unknown")
        vertical: key into VERTICAL_DEFAULTS (default "immigration_attorney")
        purpose: engagement purpose (default f"{agent} search")
        case_risks: list of {risk, severity, mitigation} applied to each
                    engagement created or updated in this run
    """
    init_schema()
    today_iso = _dt.date.today().isoformat()

    docs: list[dict] = []
    for p in paths:
        path = Path(p)
        parsed = yaml.safe_load(path.read_text())
        if not isinstance(parsed, dict):
            raise ValueError(f"{path}: root must be a YAML mapping, got {type(parsed)}")
        parsed.setdefault("_source_path", str(path))
        docs.append(parsed)

    new_count = 0
    updated_count = 0
    by_agent: dict[str, int] = {}
    engagement_ids: list[int] = []

    with connect() as conn:
        for doc in docs:
            agent_tag = doc.get("agent", "unknown")
            vertical = doc.get("vertical", "immigration_attorney")
            defaults = VERTICAL_DEFAULTS.get(
                vertical, {"vendor_type": "other", "category": vertical}
            )
            purpose = doc.get("purpose") or f"{agent_tag} search {today_iso}"

            firms = doc.get("firms") or []
            for firm in firms:
                _, eid, was_new = ingest_firm(
                    conn, firm,
                    agent_tag=agent_tag,
                    purpose=purpose,
                    vendor_type=defaults["vendor_type"],
                    category=defaults["category"],
                    today_iso=today_iso,
                )
                engagement_ids.append(eid)
                if was_new:
                    new_count += 1
                else:
                    updated_count += 1
                by_agent[agent_tag] = by_agent.get(agent_tag, 0) + 1

            for cr in doc.get("case_risks") or []:
                for eid in engagement_ids:
                    add_risk(
                        conn, eid,
                        risk=cr["risk"],
                        severity=cr.get("severity", "medium"),
                        status="open",
                        identified_date=cr.get("identified_date", today_iso),
                        mitigation=cr.get("mitigation"),
                    )

    return {
        "new_vendors": new_count,
        "updated_vendors": updated_count,
        "by_agent": by_agent,
        "engagement_ids": engagement_ids,
        "docs_ingested": len(docs),
    }
