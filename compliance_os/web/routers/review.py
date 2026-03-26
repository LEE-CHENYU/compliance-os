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

# Student track field mapping: I-20 CPT fields vs employment letter
# I-20 extraction uses same fields as i983 (employer_name, start_date, etc.)
STUDENT_FIELD_MAP = {
    "employer_name": ("employer_name", "employer_name", "exact"),
    "work_location": ("work_site_address", "work_location", "fuzzy"),
    "start_date": ("start_date", "start_date", "exact"),
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

        # Human-readable entity type labels
        ENTITY_LABELS = {"smllc": "Single-member LLC", "multi_llc": "Multi-member LLC", "c_corp": "C-Corporation", "s_corp": "S-Corporation", "not_sure": "Not sure"}

        # Entity type vs filing type
        entity_type = answers.get("entity_type", "")
        form_type = tax.get("form_type", "")
        entity_match = "match"
        if entity_type == "smllc" and form_type and "1120-S" in str(form_type):
            entity_match = "mismatch"
        elif entity_type and form_type:
            entity_match = "match"
        row = ComparisonRow(check_id=check_id, field_name="entity_type", value_a=ENTITY_LABELS.get(entity_type, entity_type), value_b=form_type, match_type="logic", status=entity_match, confidence=1.0 if entity_match == "match" else 0.0)
        db.add(row)
        results.append(row)

        # Form 5472 check
        is_foreign = answers.get("owner_residency") != "us_citizen_or_pr"
        is_smllc = answers.get("entity_type") == "smllc"
        f5472 = tax.get("form_5472_present", "")
        if is_foreign and is_smllc:
            filed = str(f5472).lower() == "true"
            status = "match" if filed else "mismatch"
            row = ComparisonRow(check_id=check_id, field_name="form_5472", value_a="Required (foreign-owned LLC)", value_b="Filed" if filed else "Not found in return", match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
            db.add(row)
            results.append(row)

        # Filing form type check (1040 vs 1040-NR)
        if is_foreign and form_type:
            status = "mismatch" if form_type == "1040" else "match"
            row = ComparisonRow(check_id=check_id, field_name="form_type", value_a="Non-US person — should file 1040-NR", value_b=f"Filed {form_type}", match_type="logic", status=status, confidence=1.0 if status == "match" else 0.0)
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

    elif check.track == "student":
        # Student track: compare I-20 vs employment letter (only if both exist)
        i20 = _get_extracted_dict(check, "i20")
        emp = _get_extracted_dict(check, "employment_letter")

        # Only run CPT cross-checks if employment letter was uploaded
        if emp:
            for comp_field, (a_field, b_field, match_type) in STUDENT_FIELD_MAP.items():
                if match_type == "semantic":
                    row = ComparisonRow(check_id=check_id, field_name=comp_field, value_a=i20.get(a_field), value_b=emp.get(b_field), match_type="semantic", status="needs_review", confidence=0.5, detail="Semantic comparison")
                else:
                    cr = compare_fields(comp_field, i20.get(a_field), emp.get(b_field), match_type)
                    row = ComparisonRow(check_id=check_id, field_name=cr.field_name, value_a=cr.value_a, value_b=cr.value_b, match_type=cr.match_type, status=cr.status, confidence=cr.confidence, detail=cr.detail)
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
    i20 = _get_extracted_dict(check, "i20")
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
    elif check.track == "student":
        ctx = EvaluationContext(
            answers=check.answers or {},
            extraction_a=i20 or {},
            extraction_b=emp or {},
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

    # Generate human-readable follow-up questions.
    # Never spit jargon — translate field mismatches into plain English.
    PLAIN_QUESTIONS: dict[str, dict] = {
        # Track A (stem_opt) field mismatches
        "job_title": {
            "question": "Your documents show two different job titles. What is your actual current job title?",
            "chips_fn": lambda a, b: [a, b, "Something else"] if a and b else ["Enter your title"],
        },
        "work_location": {
            "question": "Where do you actually work day-to-day? Your documents show different locations.",
            "chips_fn": lambda a, b: [a or "Office location", b or "Other location", "I work remotely"],
        },
        "compensation": {
            "question": "Your documents show different salary amounts. What is your actual annual compensation?",
            "chips_fn": lambda a, b: [a, b, "Different amount"] if a and b else ["Enter amount"],
        },
        "start_date": {
            "question": "Your documents show different employment start dates. When did you actually start working?",
            "chips_fn": lambda a, b: [a, b, "Different date"] if a and b else ["Enter date"],
        },
        "employer_name": {
            "question": "The employer name doesn't match across your documents. What is the exact legal name of your employer?",
            "chips_fn": lambda a, b: [a, b, "Something else"] if a and b else ["Enter employer name"],
        },
        "supervisor": {
            "question": "Your documents list different supervisors. Who is your current direct supervisor?",
            "chips_fn": lambda a, b: [a, b, "Someone else"] if a and b else ["Enter name"],
        },
        "full_time": {
            "question": "Is your position full-time or part-time?",
            "chips_fn": lambda a, b: ["Full-time", "Part-time"],
        },
        "duties": {
            "question": "Do your daily work responsibilities closely relate to your degree field?",
            "chips_fn": lambda a, b: ["Yes, closely related", "Somewhat related", "Not directly related"],
        },
        # Track B (entity) field mismatches
        "entity_type": {
            "question": "We found a mismatch between your entity type and how your tax return was filed. Did you or your CPA choose to file as an S-Corporation?",
            "chips_fn": lambda a, b: ["Yes, intentionally", "No, that seems wrong", "Not sure"],
        },
        "form_5472": {
            "question": "As a foreign-owned LLC, you're required to file Form 5472 every year — even with zero revenue. Have you ever filed this form?",
            "chips_fn": lambda a, b: ["Yes, I've filed it", "No, never heard of it", "Not sure"],
        },
        "form_type": {
            "question": "Your tax return was filed as a standard 1040. As a non-US person, you may need to file 1040-NR instead. Did your CPA discuss this with you?",
            "chips_fn": lambda a, b: ["Yes, we discussed it", "No, I used TurboTax", "Not sure"],
        },
    }

    # Fallback for any field not in the lookup
    def _default_question(field: str, val_a: str | None, val_b: str | None) -> tuple[str, list[str]]:
        name = field.replace("_", " ")
        return (
            f"We found a discrepancy in your {name}. Can you confirm which is correct?",
            [val_a or "Option A", val_b or "Option B", "Not sure"],
        )

    followups = []
    for comp in check.comparisons:
        if comp.status in ("mismatch", "needs_review"):
            # Skip questions where both values are missing — nothing useful to ask
            if not comp.value_a and not comp.value_b:
                continue
            # Skip needs_review where one side is entirely empty (document didn't extract)
            if comp.status == "needs_review" and (not comp.value_a or not comp.value_b):
                continue

            entry = PLAIN_QUESTIONS.get(comp.field_name)
            if entry:
                q_text = entry["question"]
                chips = entry["chips_fn"](comp.value_a, comp.value_b)
            else:
                q_text, chips = _default_question(comp.field_name, comp.value_a, comp.value_b)

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
