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
                key_facts.append({"label": "Entity type", "value": ENTITY_LABELS.get(a["entity_type"], a["entity_type"]), "category": "entity"})
            if a.get("owner_residency"):
                key_facts.append({"label": "Owner residency", "value": RESIDENCY_LABELS.get(a["owner_residency"], a["owner_residency"]), "category": "entity"})
            if a.get("state_of_formation"):
                key_facts.append({"label": "State of formation", "value": a["state_of_formation"], "category": "entity"})
            if a.get("formation_age"):
                age_labels = {"this_year": "This year", "1_2_years": "1-2 years ago", "3_plus_years": "3+ years ago"}
                key_facts.append({"label": "Entity age", "value": age_labels.get(a["formation_age"], a["formation_age"]), "category": "entity"})

        # Extract facts from documents
        EXTRACT_FIELDS = {
            "i983": {
                "student_name": ("Full name", "immigration"),
                "sevis_number": ("SEVIS number", "immigration"),
                "school_name": ("School", "immigration"),
                "major": ("Major / field of study", "immigration"),
                "employer_name": ("Employer", "employment"),
                "employer_ein": ("Employer EIN", "employment"),
                "job_title": ("Job title", "employment"),
                "start_date": ("Employment start", "employment"),
                "end_date": ("Employment end", "employment"),
                "compensation": ("Compensation", "employment"),
                "work_site_address": ("Work location", "employment"),
                "supervisor_name": ("Supervisor", "employment"),
            },
            "employment_letter": {
                "employee_name": ("Full name", "immigration"),
                "employer_name": ("Employer", "employment"),
                "job_title": ("Job title", "employment"),
                "compensation": ("Compensation", "employment"),
                "work_location": ("Work location", "employment"),
                "manager_name": ("Manager", "employment"),
                "start_date": ("Start date", "employment"),
            },
            "tax_return": {
                "form_type": ("Tax form filed", "tax"),
                "tax_year": ("Tax year", "tax"),
                "total_income": ("Total income", "tax"),
                "entity_name": ("Entity name", "entity"),
                "ein": ("Entity EIN", "entity"),
                "filing_status": ("Filing status", "tax"),
            },
        }
        for doc in check.documents:
            field_map = EXTRACT_FIELDS.get(doc.doc_type, {})
            for field in doc.extracted_fields:
                if field.field_name in field_map and field.field_value and field.field_value != "None":
                    label, cat = field_map[field.field_name]
                    key_facts.append({"label": label, "value": field.field_value, "category": cat})

    # Deduplicate by label (keep first)
    seen = set()
    unique_facts = []
    for f in key_facts:
        if f["label"] not in seen:
            seen.add(f["label"])
            unique_facts.append(f)

    # Build deadlines
    deadlines = _build_deadlines(checks)

    return {
        "events": events,
        "documents": all_docs,
        "findings": all_findings,
        "advisories": all_advisories,
        "upload_prompts": upload_prompts,
        "key_facts": unique_facts,
        "deadlines": deadlines,
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

    # Use the full deadline builder for next_deadline_days
    deadlines = _build_deadlines(checks)
    for d in deadlines:
        if d["days"] > 0 and (next_deadline_days is None or d["days"] < next_deadline_days):
            next_deadline_days = d["days"]

    return {
        "documents": doc_count,
        "risks": risk_count,
        "verified": verified_count,
        "next_deadline_days": next_deadline_days,
    }


def _doc_category(doc_type: str) -> str:
    if doc_type in ("i20", "i94", "i797", "i485", "i765", "i131"):
        return "immigration"
    if doc_type in ("i983", "employment_letter", "ead"):
        return "employment"
    if doc_type in ("tax_return", "w2"):
        return "tax"
    return "business"


def _build_deadlines(checks: list) -> list[dict]:
    """Build upcoming deadlines from check answers and extracted dates."""
    from dateutil.relativedelta import relativedelta

    today = date.today()
    deadlines: list[dict] = []

    for check in checks:
        a = check.answers or {}
        stage = a.get("stage", "")

        # --- Deadlines from extracted document dates ---
        for doc in check.documents:
            fields = {f.field_name: f.field_value for f in doc.extracted_fields}

            if doc.doc_type == "i983":
                # I-983 12-month evaluation
                start = fields.get("start_date")
                if start:
                    try:
                        start_dt = datetime.strptime(start, "%Y-%m-%d").date()
                        eval_due = start_dt + relativedelta(months=12)
                        days = (eval_due - today).days
                        deadlines.append({
                            "title": "I-983 12-month evaluation due",
                            "date": eval_due.isoformat(),
                            "days": days,
                            "category": "immigration",
                            "severity": "critical" if days < 0 else "warning" if days < 30 else "info",
                            "action": "Complete self-evaluation with employer signature within 10 days of anniversary",
                        })
                    except ValueError:
                        pass

                # STEM OPT / OPT end date
                end = fields.get("end_date")
                if end:
                    try:
                        end_dt = datetime.strptime(end, "%Y-%m-%d").date()
                        days = (end_dt - today).days
                        deadlines.append({
                            "title": "OPT/STEM authorization ends",
                            "date": end_dt.isoformat(),
                            "days": days,
                            "category": "immigration",
                            "severity": "critical" if days < 0 else "warning" if days < 60 else "info",
                            "action": "Ensure you have a plan: STEM extension, H-1B, or departure within 60-day grace period",
                        })

                        # Grace period
                        grace_end = end_dt + relativedelta(days=60)
                        deadlines.append({
                            "title": "60-day grace period ends",
                            "date": grace_end.isoformat(),
                            "days": (grace_end - today).days,
                            "category": "immigration",
                            "severity": "critical" if (grace_end - today).days < 0 else "warning" if (grace_end - today).days < 14 else "info",
                            "action": "Must depart the US, change status, or have a new petition filed by this date",
                        })
                    except ValueError:
                        pass

        # --- Static annual deadlines ---
        current_year = today.year

        # Tax filing: April 15
        tax_deadline = date(current_year, 4, 15)
        if tax_deadline < today:
            tax_deadline = date(current_year + 1, 4, 15)
        deadlines.append({
            "title": f"{tax_deadline.year - 1} Tax return due",
            "date": tax_deadline.isoformat(),
            "days": (tax_deadline - today).days,
            "category": "tax",
            "severity": "warning" if (tax_deadline - today).days < 30 else "info",
            "action": "File 1040-NR (if NRA) or 1040 with all schedules",
        })

        # FBAR: April 15 (auto-extension to October 15)
        fbar_deadline = date(current_year, 10, 15)
        if fbar_deadline < today:
            fbar_deadline = date(current_year + 1, 10, 15)
        years_in_us = a.get("years_in_us")
        if years_in_us and int(years_in_us) > 5:
            deadlines.append({
                "title": "FBAR filing deadline",
                "date": fbar_deadline.isoformat(),
                "days": (fbar_deadline - today).days,
                "category": "tax",
                "severity": "info",
                "action": "File FinCEN 114 if foreign accounts exceeded $10K aggregate at any point",
            })

        # Entity: state annual report
        if check.track == "entity":
            state = a.get("state_of_formation", "").lower()
            if "delaware" in state or "de" == state:
                de_deadline = date(current_year, 6, 1)
                if de_deadline < today:
                    de_deadline = date(current_year + 1, 6, 1)
                deadlines.append({
                    "title": "Delaware annual report + $300 tax due",
                    "date": de_deadline.isoformat(),
                    "days": (de_deadline - today).days,
                    "category": "entity",
                    "severity": "warning" if (de_deadline - today).days < 30 else "info",
                    "action": "File annual report and pay $300 LLC tax to maintain good standing",
                })
            elif "wyoming" in state or "wy" == state:
                # Wyoming: anniversary month
                deadlines.append({
                    "title": "Wyoming annual report due",
                    "date": f"{current_year}-12-31",
                    "days": (date(current_year, 12, 31) - today).days,
                    "category": "entity",
                    "severity": "info",
                    "action": "File annual report — due first day of anniversary month",
                })

            # Form 5472 for foreign-owned SMLLC
            owner = a.get("owner_residency")
            entity_type = a.get("entity_type")
            if owner and owner != "us_citizen_or_pr" and entity_type == "smllc":
                f5472_deadline = tax_deadline  # same as tax return
                deadlines.append({
                    "title": "Form 5472 + pro forma 1120 due",
                    "date": f5472_deadline.isoformat(),
                    "days": (f5472_deadline - today).days,
                    "category": "entity",
                    "severity": "warning" if (f5472_deadline - today).days < 30 else "info",
                    "action": "Required annually for foreign-owned single-member LLCs, even with $0 revenue",
                })

    # Deduplicate by title, keep the earliest
    seen: dict[str, dict] = {}
    for d in deadlines:
        if d["title"] not in seen or d["date"] < seen[d["title"]]["date"]:
            seen[d["title"]] = d

    # Sort by date
    result = sorted(seen.values(), key=lambda d: d["date"])
    return result
