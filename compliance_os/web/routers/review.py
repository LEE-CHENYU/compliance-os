"""Compare, evaluate, followups, snapshot endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas_v2 import (
    Comparison,
    Finding,
    Followup,
    FollowupAnswer,
    Snapshot,
)
from compliance_os.web.models.tables_v2 import (
    CheckRow,
    ComparisonRow,
    ExtractedFieldRow,
    FindingRow,
    FollowupRow,
)
from compliance_os.web.services.comparator import compare_fields
from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

router = APIRouter(prefix="/api/checks/{check_id}", tags=["review"])

# Track A field mapping: comparison_field → (i983_field, employment_letter_field, match_type)
STEM_OPT_FIELD_MAP = {
    "job_title": ("job_title", "job_title", "fuzzy"),
    "employer_name": ("employer_name", "employer_name", "exact"),
    "work_location": ("work_site_address", "work_location", "fuzzy"),
    "start_date": ("start_date", "start_date", "exact"),
    "compensation": ("compensation", "compensation", "numeric"),
    "duties": ("duties_description", "duties_description", "semantic"),
    "supervisor": ("supervisor_name", "manager_name", "fuzzy"),
    "full_time": ("full_time", "full_time", "exact"),
}

# Track B field mapping: comparison_field → (answer_key, extraction_field, match_type)
# Compares user answers against tax return extraction
ENTITY_FIELD_MAP = {
    "entity_type": ("entity_type", "form_type", "logic"),
    "form_5472": ("entity_type", "form_5472_present", "logic"),
    "form_type": ("owner_residency", "form_type", "logic"),
}


def _get_extracted_dict(check: CheckRow, doc_type: str) -> dict[str, str | None]:
    """Get extracted fields as a flat dict for a given doc type."""
    for doc in check.documents:
        if doc.doc_type == doc_type:
            return {f.field_name: f.field_value for f in doc.extracted_fields}
    return {}


@router.post("/compare", response_model=list[Comparison])
def run_comparison(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Clear old comparisons
    for old in check.comparisons:
        db.delete(old)

    results = []

    if check.track == "entity":
        # Track B: compare answers vs tax return extraction
        tax = _get_extracted_dict(check, "tax_return")
        answers = check.answers or {}

        # Entity type vs filing type
        entity_type = answers.get("entity_type", "")
        form_type = tax.get("form_type", "")
        entity_match = "match"
        if entity_type == "smllc" and form_type and "1120-S" in str(form_type):
            entity_match = "mismatch"
        elif entity_type and form_type:
            entity_match = "match"
        row = ComparisonRow(check_id=check_id, field_name="entity_type", value_a=entity_type, value_b=form_type, match_type="logic", status=entity_match, confidence=1.0 if entity_match == "match" else 0.0)
        db.add(row)
        results.append(row)

        # Form 5472 check
        is_foreign = answers.get("owner_residency") != "us_citizen_or_pr"
        is_smllc = answers.get("entity_type") == "smllc"
        f5472 = tax.get("form_5472_present", "")
        if is_foreign and is_smllc:
            status = "match" if str(f5472).lower() == "true" else "mismatch"
            row = ComparisonRow(check_id=check_id, field_name="form_5472", value_a="Required", value_b=str(f5472), match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
            db.add(row)
            results.append(row)

        # Filing form type check (1040 vs 1040-NR)
        if is_foreign and form_type:
            status = "mismatch" if form_type == "1040" else "match"
            row = ComparisonRow(check_id=check_id, field_name="form_type", value_a="NRA (should file 1040-NR)", value_b=form_type, match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
            db.add(row)
            results.append(row)

        # EIN match (just extract and show)
        ein = tax.get("ein")
        if ein:
            row = ComparisonRow(check_id=check_id, field_name="ein", value_a=None, value_b=ein, match_type="exact", status="match", confidence=1.0, detail="Extracted from return")
            db.add(row)
            results.append(row)

        # Entity name
        entity_name = tax.get("entity_name")
        if entity_name:
            row = ComparisonRow(check_id=check_id, field_name="entity_name", value_a=None, value_b=entity_name, match_type="exact", status="match", confidence=1.0, detail="Extracted from return")
            db.add(row)
            results.append(row)

    else:
        # Track A: compare I-983 vs employment letter
        i983 = _get_extracted_dict(check, "i983")
        emp = _get_extracted_dict(check, "employment_letter")

        for comp_field, (a_field, b_field, match_type) in STEM_OPT_FIELD_MAP.items():
            if match_type == "semantic":
                row = ComparisonRow(
                    check_id=check_id, field_name=comp_field,
                    value_a=i983.get(a_field), value_b=emp.get(b_field),
                    match_type="semantic", status="needs_review", confidence=0.5,
                    detail="Semantic comparison requires LLM evaluation",
                )
            else:
                cr = compare_fields(comp_field, i983.get(a_field), emp.get(b_field), match_type)
                row = ComparisonRow(
                    check_id=check_id, field_name=cr.field_name,
                    value_a=cr.value_a, value_b=cr.value_b,
                    match_type=cr.match_type, status=cr.status,
                    confidence=cr.confidence, detail=cr.detail,
                )
            db.add(row)
            results.append(row)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/comparisons", response_model=list[Comparison])
def get_comparisons(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.comparisons


@router.post("/evaluate", response_model=list[Finding])
def run_evaluation(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Build evaluation context
    i983 = _get_extracted_dict(check, "i983")
    emp = _get_extracted_dict(check, "employment_letter")
    tax = _get_extracted_dict(check, "tax_return")

    comp_dict = {}
    for c in check.comparisons:
        comp_dict[c.field_name] = {"status": c.status, "confidence": c.confidence}

    if check.track == "entity":
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a={},
            extraction_b=tax or {},
            comparisons=comp_dict,
        )
    else:
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a=i983 or {},
            extraction_b=emp or {},
            comparisons=comp_dict,
        )

    # Load rules based on track
    rule_file = str(PROJECT_ROOT / "config" / "rules" / f"{check.track}.yaml")
    engine = RuleEngine.from_yaml(rule_file)

    # Clear old findings
    for old in check.findings:
        db.delete(old)

    findings_out = []
    for fr in engine.evaluate(ctx):
        row = FindingRow(
            check_id=check_id,
            rule_id=fr.rule_id,
            rule_version=engine.version,
            severity=fr.severity,
            category=fr.category,
            title=fr.title,
            action=fr.action,
            consequence=fr.consequence,
            immigration_impact=fr.immigration_impact,
        )
        db.add(row)
        findings_out.append(row)

    check.status = "reviewed"
    db.commit()
    for r in findings_out:
        db.refresh(r)
    return findings_out


@router.get("/findings", response_model=list[Finding])
def get_findings(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.findings


@router.get("/followups", response_model=list[Followup])
def get_followups(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.followups


@router.post("/followups", response_model=list[Followup])
def generate_followups(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    # Clear old followups
    for old in check.followups:
        db.delete(old)

    # Generate follow-up questions based on mismatched comparisons
    if check.track == "entity":
        source_a = "Your answers"
        source_b = "your tax return"
    else:
        source_a = "Your I-983"
        source_b = "your employment letter"

    field_label = lambda f: f.replace("_", " ")

    followups = []
    for comp in check.comparisons:
        if comp.status in ("mismatch", "needs_review"):
            q_text = f'{source_a} show{"s" if source_a != "Your answers" else ""} "{comp.value_a}" but {source_b} shows "{comp.value_b}" for {field_label(comp.field_name)}. Which is correct?'
            chips = [
                comp.value_a or f"{source_a} value",
                comp.value_b or f"{source_b} value",
                "Something else",
            ]
            row = FollowupRow(
                check_id=check_id,
                question_key=f"{comp.field_name}_mismatch",
                question_text=q_text,
                chips=chips,
            )
            db.add(row)
            followups.append(row)

    db.commit()
    for r in followups:
        db.refresh(r)
    return followups


@router.patch("/followups/{followup_id}", response_model=Followup)
def answer_followup(
    check_id: str,
    followup_id: str,
    body: FollowupAnswer,
    db: Session = Depends(get_session),
):
    row = db.get(FollowupRow, followup_id)
    if not row or row.check_id != check_id:
        raise HTTPException(404, "Followup not found")
    row.answer = body.answer
    row.answered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.get("/snapshot")
def get_snapshot(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    extractions = {}
    for doc in check.documents:
        extractions[doc.doc_type] = doc.extracted_fields

    findings = [f for f in check.findings if f.category != "advisory"]
    advisories = [f for f in check.findings if f.category == "advisory"]

    return {
        "check": check,
        "extractions": extractions,
        "comparisons": check.comparisons,
        "findings": findings,
        "followups": check.followups,
        "advisories": advisories,
    }
