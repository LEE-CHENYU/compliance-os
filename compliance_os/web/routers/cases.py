"""Case CRUD API endpoints.

Also hosts case-scoped views over related entities — e.g. the list of
professional searches attached to a case, and a draft brief synthesised
from the case's discovery answers (used by the find-lawyer intake page
to pre-fill the textarea when launched from inside a case)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas import CaseCreate, CaseResponse, CaseListResponse
from compliance_os.web.models.tables import (
    CaseRow,
    DiscoveryAnswerRow,
    ProfessionalSearchRequestRow,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseResponse)
def create_case(body: CaseCreate, session: Session = Depends(get_session)):
    case = CaseRow(workflow_type=body.workflow_type)
    session.add(case)
    session.commit()
    session.refresh(case)
    return CaseResponse(
        id=case.id,
        workflow_type=case.workflow_type,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("", response_model=CaseListResponse)
def list_cases(session: Session = Depends(get_session)):
    cases = session.query(CaseRow).order_by(CaseRow.created_at.desc()).all()
    return CaseListResponse(cases=[
        CaseResponse(
            id=c.id, workflow_type=c.workflow_type, status=c.status,
            created_at=c.created_at, updated_at=c.updated_at,
            document_count=len(c.documents), answer_count=len(c.discovery_answers),
        )
        for c in cases
    ])


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, session: Session = Depends(get_session)):
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse(
        id=case.id, workflow_type=case.workflow_type, status=case.status,
        created_at=case.created_at, updated_at=case.updated_at,
        document_count=len(case.documents), answer_count=len(case.discovery_answers),
    )


# ----------------------- professional searches ------------------------
#
# Slim summary schema for the case "Lawyers" tab. Returns only the fields
# the list view renders — keeps payloads small even when firms_data is
# large. The full row is still available via /api/professional-search/{id}.

class _TopFirm(BaseModel):
    name: str
    confidence: int | None = None


class ProfessionalSearchSummary(BaseModel):
    id: str
    status: str
    purpose: str
    vertical: str
    created_at: str
    completed_at: str | None
    paid_at: str | None
    firm_count: int
    top_firms: list[_TopFirm]


def _summarize_search(row: ProfessionalSearchRequestRow) -> ProfessionalSearchSummary:
    firms = list(row.firms_data or [])
    return ProfessionalSearchSummary(
        id=row.id,
        status=row.status,
        purpose=row.purpose,
        vertical=row.vertical,
        created_at=row.created_at.isoformat() if row.created_at else "",
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        paid_at=row.paid_at.isoformat() if row.paid_at else None,
        firm_count=len(firms),
        top_firms=[
            _TopFirm(name=f.get("name") or "(unnamed)", confidence=f.get("confidence"))
            for f in firms[:3]
        ],
    )


@router.get(
    "/{case_id}/professional-searches",
    response_model=list[ProfessionalSearchSummary],
)
def list_case_searches(case_id: str, session: Session = Depends(get_session)):
    """List every professional search attached to this case (newest first)."""
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    rows = (
        session.query(ProfessionalSearchRequestRow)
        .filter(ProfessionalSearchRequestRow.case_id == case_id)
        .order_by(ProfessionalSearchRequestRow.created_at.desc())
        .all()
    )
    return [_summarize_search(r) for r in rows]


# ----------------------- draft brief synthesis ------------------------
#
# When the find-lawyer intake is launched from a case (?case_id=...),
# we pre-fill the case-brief textarea with a structured summary built
# from the case's discovery answers. The user can edit before submitting.
#
# Vertical inference: workflow_type → default vertical, with one
# refinement for EB-5 (when surfaced by the immigration sub-questions).


class DraftBrief(BaseModel):
    brief: str
    suggested_vertical: str
    suggested_purpose: str


_TRACK_VERTICAL = {
    "tax": "tax_attorney",
    "immigration": "immigration_attorney",
    "corporate": "corporate_attorney",
}


def _suggest_vertical(workflow_type: str, answers: dict[str, Any]) -> str:
    base = _TRACK_VERTICAL.get(workflow_type, "immigration_attorney")
    if base == "immigration_attorney":
        cat = (answers.get("imm_visa_category") or "").lower()
        sub = " ".join(answers.get("imm_subdomain") or []).lower()
        if "eb-5" in cat or "eb5" in cat or "eb-5" in sub or "eb5" in sub:
            return "immigration_eb5"
    return base


def _suggest_purpose(workflow_type: str, answers: dict[str, Any]) -> str:
    if workflow_type == "immigration":
        cat = answers.get("imm_visa_category") or "Immigration"
        return f"{cat} representation"
    if workflow_type == "tax":
        stage = answers.get("tax_filing_stage") or "Tax"
        return f"{stage} attorney"
    if workflow_type == "corporate":
        return "Corporate counsel"
    return "Legal representation"


def _fmt_value(v: Any) -> str:
    if isinstance(v, dict):
        # date+description pairs (timeline_urgency) and entity dicts
        if "date" in v or "description" in v:
            date = (v.get("date") or "").strip()
            desc = (v.get("description") or "").strip()
            return " — ".join(p for p in [date, desc] if p)
        if "name" in v:
            bits = [v.get("name", ""), v.get("type", ""), v.get("state", "")]
            return ", ".join(p for p in bits if p)
        return ", ".join(f"{k}: {x}" for k, x in v.items() if x)
    if isinstance(v, list):
        if not v:
            return ""
        return "; ".join(_fmt_value(item) for item in v if item)
    return str(v).strip()


# Section labels in the order they should appear in the synthesised brief.
# Keys not in this map are still appended at the end under a generic header.
_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Situation", [
        ("concern_area", "Concerns"),
        ("timeline_urgency", "Timeline"),
        ("existing_help", "Existing professional help"),
    ]),
    ("Tax", [
        ("tax_residency_status", "Residency status"),
        ("tax_filing_stage", "Filing stage"),
        ("tax_prior_filings", "Prior filings"),
        ("tax_income_sources", "Income sources"),
        ("tax_entities", "Entities"),
    ]),
    ("Immigration", [
        ("imm_visa_category", "Visa category"),
        ("imm_subdomain", "Sub-domain"),
        ("imm_stage", "Case stage"),
    ]),
    ("Corporate", [
        ("corp_entities", "Entities"),
        ("corp_obligations", "Obligations"),
    ]),
]


def _synthesize_brief(workflow_type: str, answers: dict[str, Any]) -> str:
    track_label = {
        "tax": "tax",
        "immigration": "immigration",
        "corporate": "corporate",
    }.get(workflow_type, workflow_type or "legal")
    article = "an" if track_label[:1] in {"a", "e", "i", "o", "u"} else "a"
    parts: list[str] = [
        f"I'm working through {article} {track_label} matter and have completed Guardian's intake. "
        "Below is the structured summary of my situation."
    ]
    used_keys: set[str] = set()
    for section_name, fields in _SECTIONS:
        rendered: list[str] = []
        for key, label in fields:
            if key not in answers:
                continue
            value = _fmt_value(answers[key])
            if not value:
                continue
            rendered.append(f"- {label}: {value}")
            used_keys.add(key)
        if rendered:
            parts.append("")
            parts.append(f"## {section_name}")
            parts.extend(rendered)

    extras = [
        (k, v) for k, v in answers.items()
        if k not in used_keys and _fmt_value(v)
    ]
    if extras:
        parts.append("")
        parts.append("## Other")
        for k, v in extras:
            parts.append(f"- {k.replace('_', ' ').title()}: {_fmt_value(v)}")

    parts.append("")
    parts.append(
        "Looking for a firm that fits the situation above. Please tailor "
        "the search to the specifics — strong preference for verifiable "
        "credentials over marketing claims."
    )
    return "\n".join(parts)


@router.get("/{case_id}/draft-brief", response_model=DraftBrief)
def get_draft_brief(case_id: str, session: Session = Depends(get_session)):
    """Synthesise a case brief + vertical guess from discovery answers.

    Used by `/find-lawyer?case_id=...` to pre-fill the intake form.
    Returns an empty-ish brief if the case has no answers — the
    frontend can still show the page; the user fills in manually.
    """
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    rows = (
        session.query(DiscoveryAnswerRow)
        .filter(DiscoveryAnswerRow.case_id == case_id)
        .all()
    )
    answers: dict[str, Any] = {r.question_key: r.answer for r in rows}
    return DraftBrief(
        brief=_synthesize_brief(case.workflow_type, answers),
        suggested_vertical=_suggest_vertical(case.workflow_type, answers),
        suggested_purpose=_suggest_purpose(case.workflow_type, answers),
    )
