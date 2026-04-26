"""Case CRUD API endpoints.

Also hosts case-scoped views over related entities — e.g. the list of
professional searches attached to a case, and a draft brief synthesised
from the case's discovery answers (used by the find-lawyer intake page
to pre-fill the textarea when launched from inside a case)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas import CaseCreate, CaseResponse, CaseListResponse
from compliance_os.web.models.tables import (
    CaseRow,
    DiscoveryAnswerRow,
    EmailThreadRow,
    ENGAGEMENT_STATUSES,
    LawyerEngagementRow,
    ProfessionalSearchRequestRow,
)
from compliance_os.web.services.case_access import get_case_for_user, maybe_user_id

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseResponse)
def create_case(
    body: CaseCreate,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """Create a case. Authenticated callers get user_id stamped immediately;
    anonymous callers create a NULL-owner case that auto-claims on the
    first authenticated access (see case_access.get_case_for_user)."""
    user_id = maybe_user_id(authorization, session)
    case = CaseRow(workflow_type=body.workflow_type, user_id=user_id)
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
def list_cases(
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """List cases scoped strictly to the calling user.

    Authenticated callers see only their own cases. Anonymous callers
    get an empty list — anonymous case URLs remain accessible directly
    via /api/cases/{id}, where case_access auto-claims them on first
    authenticated touch. Listing them here would (a) leak strangers'
    NULL-owner cases to any logged-in user and (b) provide nothing
    actionable to anonymous callers since they can't prove ownership.
    """
    user_id = maybe_user_id(authorization, session)
    if user_id is None:
        return CaseListResponse(cases=[])
    cases = (
        session.query(CaseRow)
        .filter(CaseRow.user_id == user_id)
        .order_by(CaseRow.created_at.desc())
        .all()
    )
    return CaseListResponse(cases=[
        CaseResponse(
            id=c.id, workflow_type=c.workflow_type, status=c.status,
            created_at=c.created_at, updated_at=c.updated_at,
            document_count=len(c.documents), answer_count=len(c.discovery_answers),
        )
        for c in cases
    ])


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    case = get_case_for_user(case_id, maybe_user_id(authorization, session), session)
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
def list_case_searches(
    case_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """List every professional search attached to this case (newest first)."""
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
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


# ---------------------------- engagements -----------------------------
#
# CRM-style tracking of lawyer outreach per case. Each engagement is one
# firm the user is working with — created either from a search result
# ("Track this firm") or manually for off-platform contacts. Status is
# the funnel state; notes capture freeform user observations.
#
# Cuts later in this feature will populate `firm_emails` automatically
# from search results, and the Gmail sync worker will use that list to
# match incoming threads to engagements. For Cut 1 the schema is in
# place but only the manual surfaces are wired.


class EngagementCreate(BaseModel):
    firm_name: str
    firm_emails: list[str] = []
    firm_phone: str | None = None
    firm_website: str | None = None
    firm_lead_attorney: str | None = None
    search_id: str | None = None
    notes: str | None = None
    # Allow setting a non-default status at creation, e.g. "outreach_sent"
    # when this row is created in response to the user clicking "Email firm".
    status: str | None = None


class EngagementUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    # Allow editing the firm_emails list — needed for engagements created
    # via "+ Add firm" (where contact info wasn't pulled from a search) so
    # the user can add emails for Gmail sync to match against.
    firm_emails: list[str] | None = None


class EngagementResponse(BaseModel):
    id: str
    case_id: str
    search_id: str | None
    firm_name: str
    firm_emails: list[str]
    firm_phone: str | None
    firm_website: str | None
    firm_lead_attorney: str | None
    status: str
    notes: str | None
    created_at: str
    last_activity_at: str


def _serialize_engagement(row: LawyerEngagementRow) -> EngagementResponse:
    return EngagementResponse(
        id=row.id,
        case_id=row.case_id,
        search_id=row.search_id,
        firm_name=row.firm_name,
        firm_emails=list(row.firm_emails or []),
        firm_phone=row.firm_phone,
        firm_website=row.firm_website,
        firm_lead_attorney=row.firm_lead_attorney,
        status=row.status,
        notes=row.notes,
        created_at=row.created_at.isoformat() if row.created_at else "",
        last_activity_at=row.last_activity_at.isoformat() if row.last_activity_at else "",
    )


def _validate_status(status: str) -> str:
    if status not in ENGAGEMENT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status '{status}'. Must be one of: "
                + ", ".join(ENGAGEMENT_STATUSES)
            ),
        )
    return status


@router.get(
    "/{case_id}/engagements",
    response_model=list[EngagementResponse],
)
def list_engagements(
    case_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
    rows = (
        session.query(LawyerEngagementRow)
        .filter(LawyerEngagementRow.case_id == case_id)
        .order_by(LawyerEngagementRow.last_activity_at.desc())
        .all()
    )
    return [_serialize_engagement(r) for r in rows]


def _hydrate_from_search(
    session: Session, search_id: str, firm_name: str
) -> dict[str, Any]:
    """Pull firm contact info out of a completed search's firms_data.

    Returns a dict of fields suitable for splatting into LawyerEngagementRow
    kwargs. Empty dict if the search doesn't exist, isn't complete, or
    doesn't contain a matching firm — caller should still honor whatever
    contact info the request body provided.
    """
    search = session.get(ProfessionalSearchRequestRow, search_id)
    if search is None or not search.firms_data:
        return {}
    target = firm_name.strip().lower()
    for f in search.firms_data:
        name = (f.get("name") or "").strip()
        if name.lower() != target:
            continue
        emails = [
            e for e in [f.get("email")] if e and isinstance(e, str)
        ]
        return {
            "firm_emails": emails,
            "firm_phone": f.get("phone") or None,
            "firm_website": f.get("website") or None,
            "firm_lead_attorney": f.get("lead_attorney") or None,
        }
    return {}


@router.post(
    "/{case_id}/engagements",
    response_model=EngagementResponse,
)
def create_engagement(
    case_id: str,
    body: EngagementCreate,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
    if not body.firm_name.strip():
        raise HTTPException(status_code=400, detail="firm_name cannot be empty")

    status = _validate_status(body.status) if body.status else "not_contacted"

    # Soft dedupe: if an engagement for the same firm name already exists
    # on this case, return that row instead of creating a duplicate. The
    # most common cause is the user double-clicking "Track" — we prefer
    # idempotent over strict.
    existing = (
        session.query(LawyerEngagementRow)
        .filter(
            LawyerEngagementRow.case_id == case_id,
            LawyerEngagementRow.firm_name == body.firm_name.strip(),
        )
        .first()
    )
    if existing is not None:
        return _serialize_engagement(existing)

    # When the engagement comes from a search result, copy the firm's
    # contact info from firms_data. The body-provided fields win when
    # both are present (caller can override).
    hydrated: dict[str, Any] = {}
    if body.search_id:
        hydrated = _hydrate_from_search(session, body.search_id, body.firm_name)

    body_emails = [e.strip() for e in body.firm_emails if e and e.strip()]
    row = LawyerEngagementRow(
        case_id=case_id,
        search_id=body.search_id,
        firm_name=body.firm_name.strip(),
        firm_emails=body_emails or hydrated.get("firm_emails") or [],
        firm_phone=body.firm_phone or hydrated.get("firm_phone"),
        firm_website=body.firm_website or hydrated.get("firm_website"),
        firm_lead_attorney=body.firm_lead_attorney or hydrated.get("firm_lead_attorney"),
        status=status,
        notes=body.notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _serialize_engagement(row)


@router.patch(
    "/{case_id}/engagements/{engagement_id}",
    response_model=EngagementResponse,
)
def update_engagement(
    case_id: str,
    engagement_id: str,
    body: EngagementUpdate,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
    row = session.get(LawyerEngagementRow, engagement_id)
    if row is None or row.case_id != case_id:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if body.status is not None:
        row.status = _validate_status(body.status)
    if body.notes is not None:
        row.notes = body.notes
    if body.firm_emails is not None:
        row.firm_emails = [e.strip() for e in body.firm_emails if e and e.strip()]

    session.commit()
    session.refresh(row)
    return _serialize_engagement(row)


class DraftEmail(BaseModel):
    to: list[str]
    subject: str
    body: str


def _truncate_brief(brief: str, max_chars: int = 800) -> str:
    """Trim the case brief to a single email-friendly paragraph.

    The synthesized brief is markdown with section headers; for an outbound
    email we strip the headers and keep the first ~800 chars of substantive
    content. Users can hand-edit before sending.
    """
    if not brief:
        return ""
    # Drop markdown headers and bullet markers; collapse to plain prose.
    lines: list[str] = []
    for raw in brief.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        lines.append(line)
    text = " ".join(lines).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def _firm_why_fit(
    session: Session, search_id: str | None, firm_name: str
) -> str | None:
    """Return the search agent's why-this-firm-fits paragraph if available."""
    if not search_id:
        return None
    search = session.get(ProfessionalSearchRequestRow, search_id)
    if search is None or not search.firms_data:
        return None
    target = firm_name.strip().lower()
    for f in search.firms_data:
        if (f.get("name") or "").strip().lower() != target:
            continue
        # _why_fits is a list of [persona_id, text] pairs (deduped across
        # personas in the aggregator). Take the first — they all describe
        # the same firm, so any one is a defensible paraphrase.
        whys = f.get("_why_fits") or []
        if whys and isinstance(whys, list):
            first = whys[0]
            if isinstance(first, list) and len(first) >= 2:
                return str(first[1])
        return None
    return None


@router.get(
    "/{case_id}/engagements/{engagement_id}/draft-email",
    response_model=DraftEmail,
)
def draft_engagement_email(
    case_id: str,
    engagement_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """Synthesize a first-touch email for the user to send to this firm.

    Subject + body are written first-person from the user's perspective,
    using the case brief and (when available) the search agent's why-fit
    rationale for this specific firm. The user opens it via mailto: and
    edits before sending.
    """
    row = session.get(LawyerEngagementRow, engagement_id)
    if row is None or row.case_id != case_id:
        raise HTTPException(status_code=404, detail="Engagement not found")

    case = get_case_for_user(case_id, maybe_user_id(authorization, session), session)

    # Build the brief from discovery answers (same synthesis used at intake).
    answer_rows = (
        session.query(DiscoveryAnswerRow)
        .filter(DiscoveryAnswerRow.case_id == case_id)
        .all()
    )
    answers: dict[str, Any] = {r.question_key: r.answer for r in answer_rows}
    brief_text = _truncate_brief(_synthesize_brief(case.workflow_type, answers))

    vertical_label = case.workflow_type.replace("_", " ") if case.workflow_type else "legal"
    purpose_seed = _suggest_purpose(case.workflow_type, answers)
    subject = f"Inquiry — {purpose_seed}"

    greeting = (
        f"Hi {row.firm_lead_attorney},"
        if row.firm_lead_attorney
        else f"Hi {row.firm_name} team,"
    )

    why_fit = _firm_why_fit(session, row.search_id, row.firm_name)
    why_fit_paragraph = (
        f"\n\nI came across your firm during my research — what stood out: "
        f"{why_fit.strip()}\n"
        if why_fit
        else ""
    )

    body_lines = [
        greeting,
        "",
        f"I'm looking for {vertical_label} representation for the following situation:",
        "",
        brief_text or "(I'll share the full case brief on a call.)",
        why_fit_paragraph.rstrip(),
        "",
        "Could we schedule a 30-minute consultation? Open to your preferred timing.",
        "",
        "Best,",
    ]
    body = "\n".join(line for line in body_lines if line is not None)

    return DraftEmail(
        to=list(row.firm_emails or []),
        subject=subject,
        body=body,
    )


class EmailThreadResponse(BaseModel):
    id: str
    gmail_thread_id: str
    subject: str
    last_message_at: str
    last_message_snippet: str
    last_message_from: str
    last_message_direction: str  # inbound | outbound
    message_count: int


@router.get(
    "/{case_id}/engagements/{engagement_id}/threads",
    response_model=list[EmailThreadResponse],
)
def list_engagement_threads(
    case_id: str,
    engagement_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """List email threads matched to this engagement (newest first)."""
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
    row = session.get(LawyerEngagementRow, engagement_id)
    if row is None or row.case_id != case_id:
        raise HTTPException(status_code=404, detail="Engagement not found")
    threads = (
        session.query(EmailThreadRow)
        .filter(EmailThreadRow.engagement_id == engagement_id)
        .order_by(EmailThreadRow.last_message_at.desc())
        .all()
    )
    return [
        EmailThreadResponse(
            id=t.id,
            gmail_thread_id=t.gmail_thread_id,
            subject=t.subject,
            last_message_at=t.last_message_at.isoformat() if t.last_message_at else "",
            last_message_snippet=t.last_message_snippet,
            last_message_from=t.last_message_from,
            last_message_direction=t.last_message_direction,
            message_count=t.message_count,
        )
        for t in threads
    ]


@router.delete("/{case_id}/engagements/{engagement_id}")
def delete_engagement(
    case_id: str,
    engagement_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    get_case_for_user(case_id, maybe_user_id(authorization, session), session)
    row = session.get(LawyerEngagementRow, engagement_id)
    if row is None or row.case_id != case_id:
        raise HTTPException(status_code=404, detail="Engagement not found")
    session.delete(row)
    session.commit()
    return {"ok": True}


@router.get("/{case_id}/draft-brief", response_model=DraftBrief)
def get_draft_brief(
    case_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """Synthesise a case brief + vertical guess from discovery answers.

    Used by `/find-lawyer?case_id=...` to pre-fill the intake form.
    Returns an empty-ish brief if the case has no answers — the
    frontend can still show the page; the user fills in manually.
    """
    case = get_case_for_user(case_id, maybe_user_id(authorization, session), session)
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
