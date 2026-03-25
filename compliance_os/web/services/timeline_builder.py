"""Build timeline events from user's checks, documents, and findings."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, FindingRow


def build_timeline(user_id: str, db: Session) -> dict:
    """Build a full timeline for a user from their checks and documents."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()

    events: list[dict[str, Any]] = []
    all_docs: list[dict] = []
    all_findings: list[dict] = []
    all_advisories: list[dict] = []
    upload_prompts: list[dict] = []

    doc_types_uploaded: set[str] = set()

    for check in checks:
        # Collect documents
        for doc in check.documents:
            doc_types_uploaded.add(doc.doc_type)
            doc_data = {
                "id": doc.id,
                "filename": doc.filename,
                "doc_type": doc.doc_type,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "category": _doc_category(doc.doc_type),
            }
            all_docs.append(doc_data)

        # Extract dates from extracted fields to create timeline events
        for doc in check.documents:
            fields = {f.field_name: f.field_value for f in doc.extracted_fields}

            if doc.doc_type == "i983":
                if fields.get("start_date"):
                    events.append({
                        "date": fields["start_date"],
                        "title": "STEM OPT started",
                        "type": "milestone",
                        "category": "immigration",
                        "documents": [d for d in all_docs if d["doc_type"] in ("i983", "employment_letter")],
                    })
                if fields.get("end_date"):
                    events.append({
                        "date": fields["end_date"],
                        "title": "STEM OPT ends",
                        "type": "deadline",
                        "category": "immigration",
                        "documents": [],
                    })

            if doc.doc_type == "tax_return":
                tax_year = fields.get("tax_year")
                if tax_year:
                    events.append({
                        "date": f"{tax_year}-04-15",
                        "title": f"{tax_year} Tax Return filed",
                        "type": "filing",
                        "category": "tax",
                        "documents": [d for d in all_docs if d["doc_type"] == "tax_return"],
                    })

        # Collect findings and advisories
        for finding in check.findings:
            f_data = {
                "id": finding.id,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "category": finding.category,
                "title": finding.title,
                "action": finding.action,
                "consequence": finding.consequence,
                "immigration_impact": finding.immigration_impact,
            }
            if finding.category == "advisory":
                all_advisories.append(f_data)
            else:
                all_findings.append(f_data)

    # Add "today" marker
    today = date.today().isoformat()
    events.append({
        "date": today,
        "title": "Today",
        "type": "now",
        "category": None,
        "documents": [],
    })

    # Generate upload prompts based on what's missing
    if checks:
        stage = None
        for c in checks:
            if c.answers and c.answers.get("stage"):
                stage = c.answers["stage"]

        if stage in ("stem_opt", "opt") and "i983" not in doc_types_uploaded:
            upload_prompts.append({
                "doc_type": "i983",
                "prompt": "Upload your I-983 Training Plan",
                "why": "Needed to verify your STEM OPT authorization and employer details.",
            })

        if "employment_letter" not in doc_types_uploaded:
            upload_prompts.append({
                "doc_type": "employment_letter",
                "prompt": "Upload your employment letter",
                "why": "Cross-checks job title, salary, and location against your I-983.",
            })

        # Check for 12-month eval
        for check in checks:
            for doc in check.documents:
                if doc.doc_type == "i983":
                    fields = {f.field_name: f.field_value for f in doc.extracted_fields}
                    start = fields.get("start_date")
                    if start:
                        try:
                            start_date = datetime.strptime(start, "%Y-%m-%d").date()
                            from dateutil.relativedelta import relativedelta
                            eval_due = start_date + relativedelta(months=12)
                            if date.today() > eval_due:
                                upload_prompts.append({
                                    "doc_type": "i983_evaluation",
                                    "prompt": "Upload your completed 12-month evaluation",
                                    "why": f"Due by {eval_due.isoformat()}. Must be signed by employer within 10 days of anniversary.",
                                    "event_date": eval_due.isoformat(),
                                })
                        except ValueError:
                            pass

    # Sort events by date
    events.sort(key=lambda e: e["date"])

    # Attach findings to relevant events
    for event in events:
        event["risks"] = []
    # Attach findings to the closest event
    for finding in all_findings:
        if events:
            # Attach to "today" event
            for event in events:
                if event["type"] == "now":
                    event.setdefault("risks", []).append(finding)
                    break

    # Build key facts from check answers
    STAGE_LABELS = {
        "pre_completion": "CPT (Pre-completion)",
        "opt": "Post-completion OPT",
        "stem_opt": "STEM OPT Extension",
        "h1b": "H-1B",
        "i140": "I-140 / Green Card",
        "not_sure": "Not sure",
    }
    ENTITY_LABELS = {
        "smllc": "Single-member LLC",
        "multi_llc": "Multi-member LLC",
        "c_corp": "C-Corporation",
        "s_corp": "S-Corporation",
    }
    RESIDENCY_LABELS = {
        "us_citizen_or_pr": "US Citizen / PR",
        "on_visa": "On a visa",
        "outside_us": "Outside US",
    }
    EMPLOYMENT_LABELS = {
        "employed": "Employed",
        "between_jobs": "Between jobs",
        "not_employed": "Not employed",
    }

    key_facts: list[dict[str, str]] = []
    for check in checks:
        a = check.answers or {}
        if check.track == "stem_opt":
            if a.get("stage"):
                key_facts.append({"label": "Immigration stage", "value": STAGE_LABELS.get(a["stage"], a["stage"])})
            if a.get("years_in_us"):
                key_facts.append({"label": "Years in US", "value": f"{a['years_in_us']} years"})
            if a.get("employment_status"):
                key_facts.append({"label": "Employment", "value": EMPLOYMENT_LABELS.get(a["employment_status"], a["employment_status"])})
            if a.get("employer_changed") == "yes":
                key_facts.append({"label": "Changed employers", "value": "Yes"})
            if a.get("petition_status"):
                key_facts.append({"label": "Petition status", "value": a["petition_status"].capitalize()})
        elif check.track == "entity":
            if a.get("entity_type"):
                key_facts.append({"label": "Entity type", "value": ENTITY_LABELS.get(a["entity_type"], a["entity_type"])})
            if a.get("owner_residency"):
                key_facts.append({"label": "Owner residency", "value": RESIDENCY_LABELS.get(a["owner_residency"], a["owner_residency"])})
            if a.get("state_of_formation"):
                key_facts.append({"label": "State", "value": a["state_of_formation"]})

    # Deduplicate by label (keep first)
    seen = set()
    unique_facts = []
    for f in key_facts:
        if f["label"] not in seen:
            seen.add(f["label"])
            unique_facts.append(f)

    return {
        "events": events,
        "documents": all_docs,
        "findings": all_findings,
        "advisories": all_advisories,
        "upload_prompts": upload_prompts,
        "key_facts": unique_facts,
    }


def build_stats(user_id: str, db: Session) -> dict:
    """Build aggregate stats for the user's dashboard."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()

    doc_count = 0
    risk_count = 0
    verified_count = 0
    next_deadline_days = None

    for check in checks:
        doc_count += len(check.documents)
        for f in check.findings:
            if f.category != "advisory":
                risk_count += 1
        for c in check.comparisons:
            if c.status == "match":
                verified_count += 1

        # Find next deadline from extracted end dates
        for doc in check.documents:
            for field in doc.extracted_fields:
                if field.field_name == "end_date" and field.field_value:
                    try:
                        end = datetime.strptime(field.field_value, "%Y-%m-%d").date()
                        days = (end - date.today()).days
                        if days > 0 and (next_deadline_days is None or days < next_deadline_days):
                            next_deadline_days = days
                    except ValueError:
                        pass

    return {
        "documents": doc_count,
        "risks": risk_count,
        "verified": verified_count,
        "next_deadline_days": next_deadline_days,
    }


def _doc_category(doc_type: str) -> str:
    if doc_type in ("i983", "employment_letter", "ead", "i94", "i797"):
        return "immigration"
    if doc_type in ("tax_return",):
        return "tax"
    return "entity"
