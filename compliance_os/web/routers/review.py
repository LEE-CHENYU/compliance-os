"""Compare, evaluate, followups, snapshot endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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

# Field mapping: comparison_field → (i983_field, employment_letter_field, match_type)
FIELD_MAP = {
    "job_title": ("job_title", "job_title", "fuzzy"),
    "employer_name": ("employer_name", "employer_name", "exact"),
    "work_location": ("work_site_address", "work_location", "fuzzy"),
    "start_date": ("start_date", "start_date", "exact"),
    "compensation": ("compensation", "compensation", "numeric"),
    "duties": ("duties_description", "duties_description", "semantic"),
    "supervisor": ("supervisor_name", "manager_name", "fuzzy"),
    "full_time": ("full_time", "full_time", "exact"),
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

    i983 = _get_extracted_dict(check, "i983")
    emp = _get_extracted_dict(check, "employment_letter")

    # Clear old comparisons
    for old in check.comparisons:
        db.delete(old)

    results = []
    for comp_field, (a_field, b_field, match_type) in FIELD_MAP.items():
        if match_type == "semantic":
            # Semantic comparison placeholder — store as needs_review for now
            row = ComparisonRow(
                check_id=check_id,
                field_name=comp_field,
                value_a=i983.get(a_field),
                value_b=emp.get(b_field),
                match_type="semantic",
                status="needs_review",
                confidence=0.5,
                detail="Semantic comparison requires LLM evaluation",
            )
        else:
            cr = compare_fields(comp_field, i983.get(a_field), emp.get(b_field), match_type)
            row = ComparisonRow(
                check_id=check_id,
                field_name=cr.field_name,
                value_a=cr.value_a,
                value_b=cr.value_b,
                match_type=cr.match_type,
                status=cr.status,
                confidence=cr.confidence,
                detail=cr.detail,
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

    ctx = EvaluationContext(
        answers=check.answers or {},
        extraction_a=i983 or emp,  # Track A: i983 is doc A
        extraction_b=emp or tax,   # Track A: employment letter is doc B
        comparisons=comp_dict,
    )

    # Load rules based on track
    rule_file = f"config/rules/{check.track}.yaml"
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
    followups = []
    for comp in check.comparisons:
        if comp.status in ("mismatch", "needs_review"):
            row = FollowupRow(
                check_id=check_id,
                question_key=f"{comp.field_name}_mismatch",
                question_text=f"Your I-983 shows \"{comp.value_a}\" but your employment letter shows \"{comp.value_b}\" for {comp.field_name.replace('_', ' ')}. Which is correct?",
                chips=[comp.value_a or "I-983 value", comp.value_b or "Letter value", "Something else"],
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
