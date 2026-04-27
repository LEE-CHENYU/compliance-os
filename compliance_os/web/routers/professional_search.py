"""HTTP surface for professional search onboarding.

- `POST /api/professional-search` — user intake. Accepts a case brief
  (required) plus any number of uploaded files. Creates a
  `ProfessionalSearchRequestRow`, extracts text from uploads into the
  row's `uploaded_notes`, then kicks off the Anthropic-powered runner
  as a background task. Returns the request id so the client can poll.

- `GET /api/professional-search/{id}` — returns the current row
  (status, per-persona progress, tier report when complete).
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import io
import logging
from pathlib import Path

import yaml as _yaml
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.settings import settings
from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables import ProfessionalSearchRequestRow
from compliance_os.web.services.auth_service import get_bearer_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/professional-search", tags=["professional-search"])


MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_TEXT_PER_FILE = 4000             # chars appended to brief per file
MAX_UPLOADS = 8


# ----------------------------- helpers --------------------------------

def _extract_text(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Best-effort text extraction. Returns '' on failure — never raises."""
    try:
        ext = Path(filename).suffix.lower()
        if ext in {".txt", ".md", ".csv"} or content_type.startswith("text/"):
            return file_bytes.decode("utf-8", errors="replace")
        if ext == ".pdf" or content_type == "application/pdf":
            try:
                import fitz  # pymupdf
            except ImportError:
                return ""
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            try:
                return "\n".join(page.get_text() for page in doc)
            finally:
                doc.close()
        if ext == ".docx":
            try:
                from docx import Document as _Docx
            except ImportError:
                return ""
            return "\n".join(p.text for p in _Docx(io.BytesIO(file_bytes)).paragraphs)
    except Exception:
        return ""
    return ""


def _build_uploaded_notes(files: list[UploadFile]) -> str:
    """Concatenate trimmed text from each upload into a single notes blob."""
    parts: list[str] = []
    for f in files[:MAX_UPLOADS]:
        raw = f.file.read(MAX_UPLOAD_SIZE + 1)
        if len(raw) > MAX_UPLOAD_SIZE:
            parts.append(f"[{f.filename}: skipped — exceeds {MAX_UPLOAD_SIZE} bytes]")
            continue
        text = _extract_text(raw, f.filename or "upload", f.content_type or "")
        text = text.strip()
        if not text:
            parts.append(f"[{f.filename}: no extractable text]")
            continue
        if len(text) > MAX_TEXT_PER_FILE:
            text = text[:MAX_TEXT_PER_FILE] + f"\n... [truncated — original {len(text)} chars]"
        parts.append(f"--- {f.filename} ---\n{text}")
    return "\n\n".join(parts)


# ----------------------------- schemas --------------------------------

class SearchResponse(BaseModel):
    id: str
    status: str
    purpose: str
    vertical: str
    case_brief: str
    uploaded_notes: str | None
    persona_status: dict
    tier_report: list | None
    error: str | None
    created_at: str
    completed_at: str | None
    paid_at: str | None
    is_paid: bool
    is_claimed: bool
    stripe_customer_email: str | None
    # Set when this search was launched from inside a case (via the
    # "Find a specialist" CTA). The frontend uses it to enable the
    # per-firm "+ Track" buttons on the results page.
    case_id: str | None
    # Stage-2 enrichment lifecycle — null fields when never dispatched.
    # Frontend polls these to decide whether to show "verifying individual
    # attorney credentials..." banner above the firm list.
    enrichment_status: str = "idle"
    enrichment_started_at: str | None = None
    enrichment_completed_at: str | None = None
    enrichment_error: str | None = None


class EnrichmentStatusResponse(BaseModel):
    """Lightweight polling shape for the /paid page — we don't want every
    poll to drag the full firms_data + tier_report payload across the wire.
    """
    status: str  # idle | enriching | complete | failed
    started_at: str | None
    completed_at: str | None
    error: str | None
    # firm-level rough completion: how many firms have at least one
    # `_lead_attorney_*` field set. Lets the UI show a "X of Y firms
    # enriched" progress bar during the ~2-3 min window.
    firms_enriched: int
    firms_total: int


def _serialize(
    row: ProfessionalSearchRequestRow,
    *,
    include_pii: bool = False,
) -> SearchResponse:
    """Serialize a search row to the public API shape.

    PII gating: `case_brief`, `uploaded_notes`, and `stripe_customer_email`
    contain user-supplied / Stripe-captured personal data. The status
    page polls `GET /{request_id}` *unauthenticated* by design (the URL
    is shareable + the user might not have signed up yet). Returning
    the full brief / customer email there leaks PII to anyone who
    learns the (UUID) request_id — including via Referer headers when
    the page is shared. Pass `include_pii=True` only on auth-gated
    paths (claim, mine/list, future authenticated GETs).
    """
    return SearchResponse(
        id=row.id,
        status=row.status,
        purpose=row.purpose,
        vertical=row.vertical,
        case_brief=(row.case_brief if include_pii else ""),
        uploaded_notes=(row.uploaded_notes if include_pii else None),
        persona_status=row.persona_status or {},
        tier_report=row.tier_report,
        error=row.error,
        created_at=row.created_at.isoformat() if row.created_at else "",
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        paid_at=row.paid_at.isoformat() if row.paid_at else None,
        is_paid=row.paid_at is not None,
        is_claimed=row.user_id is not None,
        # Customer email is needed by the post-purchase page to pre-fill
        # the signup form, but only the user who's about to claim should
        # see it. Anonymous polling gets None.
        stripe_customer_email=(row.stripe_customer_email if include_pii else None),
        case_id=row.case_id,
        enrichment_status=row.enrichment_status or "idle",
        enrichment_started_at=(
            row.enrichment_started_at.isoformat() if row.enrichment_started_at else None
        ),
        enrichment_completed_at=(
            row.enrichment_completed_at.isoformat() if row.enrichment_completed_at else None
        ),
        enrichment_error=row.enrichment_error,
    )


# ----------------------------- endpoints ------------------------------

@router.post("", response_model=SearchResponse)
def create_search(
    background_tasks: BackgroundTasks,
    case_brief: str = Form(...),
    purpose: str = Form(...),
    vertical: str = Form("immigration_attorney"),
    case_id: str | None = Form(None),
    files: list[UploadFile] = File(default_factory=list),
    session: Session = Depends(get_session),
):
    """Start a new professional search.

    Multipart form (so file uploads work alongside the fields):
        case_brief: str       — user's case description (required)
        purpose: str          — short engagement label, e.g. "H-1B 2026 cap"
        vertical: str         — persona directory; defaults to immigration_attorney
        case_id: str | None   — optional existing CaseRow id to link to
        files: File[]         — up to 8 supporting docs (PDF / DOCX / TXT / MD)

    Returns the created request with status=queued. Poll GET by id for updates.
    """
    # Each search burns ~$2-3 in API + web_search calls. A meaningful
    # brief is required so agents have something to work with — 200
    # chars (~30-40 words) is the floor for useful research output.
    # Same threshold as the frontend, enforced here so the API can't be
    # bypassed via direct curl.
    MIN_BRIEF_CHARS = 200
    brief_trimmed = case_brief.strip()
    if not brief_trimmed:
        raise HTTPException(status_code=400, detail="case_brief cannot be empty")
    if len(brief_trimmed) < MIN_BRIEF_CHARS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"case_brief is too short ({len(brief_trimmed)} chars). "
                f"Each search costs real compute — please describe the "
                f"specific situation, regulatory wrinkles, location, and "
                f"timeline (minimum {MIN_BRIEF_CHARS} chars)."
            ),
        )
    if not purpose.strip():
        raise HTTPException(status_code=400, detail="purpose cannot be empty")

    uploaded_notes = _build_uploaded_notes(files) if files else None

    row = ProfessionalSearchRequestRow(
        case_id=case_id,
        case_brief=case_brief.strip(),
        purpose=purpose.strip(),
        vertical=vertical,
        status="queued",
        persona_status={},
        uploaded_notes=uploaded_notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    # Defer the actual import until now so a missing anthropic install
    # only blows up at dispatch time, not at app startup.
    from compliance_os.web.services.professional_search_runner import run_search_sync

    background_tasks.add_task(run_search_sync, row.id)
    # Submitter is the implicit owner — return the full payload so they
    # can immediately see what they posted (handy for client retries).
    return _serialize(row, include_pii=True)


# IMPORTANT: keep static-prefix routes (`/mine/list`, `/stripe-webhook`)
# defined BEFORE the catch-all `/{request_id}` below. FastAPI matches in
# declaration order; a future regression that splits these routes across
# files could shadow the static ones if the order isn't preserved.
@router.get("/mine/list", response_model=list[SearchResponse])
def list_my_searches(
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """List the authenticated user's claimed searches.

    Path is `/mine/list` (not `/mine`) so it doesn't collide with the
    `/{request_id}` route — FastAPI's `/{x}` matches one path segment,
    so the two-segment `/mine/list` is unambiguous.
    """
    payload = get_bearer_payload(authorization, db)
    rows = (
        db.query(ProfessionalSearchRequestRow)
        .filter(ProfessionalSearchRequestRow.user_id == payload["user_id"])
        .order_by(ProfessionalSearchRequestRow.created_at.desc())
        .limit(50)
        .all()
    )
    # Authenticated owner — full PII is appropriate.
    return [_serialize(r, include_pii=True) for r in rows]


@router.get("/{request_id}", response_model=SearchResponse)
def get_search(
    request_id: str,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """Get a search by id.

    Anonymous callers get a sanitized response (no `case_brief`, no
    `uploaded_notes`, no `stripe_customer_email`). The authenticated
    owner — and only the owner — gets the full row. We also accept any
    valid bearer for the implicit case where the user has logged in
    *between* search submission and the post-purchase claim, but match
    the user only after parsing the token.
    """
    row = session.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")

    include_pii = False
    if authorization:
        try:
            payload = get_bearer_payload(authorization, session)
            if row.user_id and row.user_id == payload.get("user_id"):
                include_pii = True
        except HTTPException:
            # Bad / missing token — fall through to anonymous response.
            pass

    return _serialize(row, include_pii=include_pii)


# --- Guardian marketplace upsell ---
#
# Returns 0–2 Guardian products that fit this search's vertical+brief.
# Empty list when nothing fits (e.g. EB-5 — Guardian has no equivalent
# in-house product; the user should hire an external firm). The frontend
# only renders the upsell card when this list is non-empty, so an empty
# response is a normal valid state, not an error.


class MarketplaceMatch(BaseModel):
    sku: str
    name: str
    public_name: str | None = None
    description: str
    public_description: str | None = None
    price_cents: int
    headline: str | None = None
    public_headline: str | None = None
    cta_label: str | None = None
    public_cta_label: str | None = None
    path: str | None = None
    match_score: int
    match_reason: str


@router.get(
    "/{request_id}/marketplace-match",
    response_model=list[MarketplaceMatch],
)
def get_marketplace_match(request_id: str, session: Session = Depends(get_session)):
    """Recommend Guardian marketplace products that fit this search.

    Used by the search results page to render an upsell card above the
    external-firm tier list — closes the funnel for users whose situation
    matches a Guardian product we can fulfill in-house.
    """
    row = session.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    from compliance_os.web.services.marketplace_match import match_products
    matches = match_products(vertical=row.vertical, case_brief=row.case_brief)
    return [MarketplaceMatch(**m) for m in matches]


# Note: there is intentionally no unauthenticated `GET /api/professional-search`
# list endpoint. Search briefs frequently contain PII (names, employers,
# regulatory specifics), and returning them across users would be a leak.
# If a list view is needed later, scope it to the authenticated user.


# ---------------------------- Report rendering ----------------------------
#
# Two output formats:
#
#   - HTML (default; opens in a new tab, prints cleanly to PDF) — the
#     polished, user-facing artifact. Firms are deduplicated across
#     personas; the same firm with rationales from multiple search
#     axes shows once with all rationales aggregated.
#
#   - Markdown (`?format=md`) — for power users who want to pipe results
#     into another tool. Keeps the persona-grouped structure since
#     markdown lacks anchor / styling affordances for cross-referencing.


PERSONA_LABELS = {
    # Generic immigration set
    "elite_boutique": "Elite boutiques",
    "startup_founder": "Startup / founder-focused",
    "litigation_contrarian": "Federal-court litigators",
    # EB-5 set
    "eb5_specialist": "EB-5 specialists",
    "securities_sophisticated": "Securities-sophisticated",
    "source_of_funds": "Source-of-funds specialists",
}


def _persona_label(persona_id: str) -> str:
    """Pretty label, with a graceful fallback for tuned personas."""
    if persona_id in PERSONA_LABELS:
        return PERSONA_LABELS[persona_id]
    if persona_id.startswith("tuned_"):
        rest = persona_id[len("tuned_"):].replace("_", " ").title()
        return f"Tuned · {rest}"
    return persona_id.replace("_", " ").title()


# Aggregation helpers live in `compliance_os.professional_search.aggregator`
# (package layer, not web layer) so the background runner can import them
# without a runner→router back-edge. Local aliases keep the existing
# call sites in this file unchanged.
from compliance_os.professional_search.aggregator import (
    aggregate_firms as _aggregate_firms_impl,
    load_persona_yamls as _load_persona_yamls_impl,
)


def _load_persona_yamls(row: ProfessionalSearchRequestRow) -> dict[str, dict]:
    return _load_persona_yamls_impl(row)


def _aggregate_firms(persona_yamls: dict[str, dict]) -> list[dict]:
    return _aggregate_firms_impl(persona_yamls)


def _score_tier(score: int | None) -> tuple[str, str]:
    """(tier-letter, color-class) for a 0-100 confidence score."""
    if score is None:
        return ("?", "tier-unknown")
    if score >= 90:
        return ("S", "tier-s")
    if score >= 80:
        return ("A", "tier-a")
    if score >= 70:
        return ("B", "tier-b")
    if score >= 60:
        return ("C", "tier-c")
    return ("D", "tier-d")


def _slug(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")[:60]


def _render_html(row: ProfessionalSearchRequestRow) -> str:
    """Render a presentable, print-friendly HTML report.

    Self-contained: all CSS inlined, no external assets, opens in any
    browser. Designed for both screen viewing and Print-to-PDF.

    Data sources, in priority order:
      1. `row.firms_data` — DB-resident aggregated firm dossiers
         (canonical for any search run after this column was added)
      2. on-disk persona YAMLs — fallback for older rows
    """
    firms: list[dict] = []
    persona_yamls: dict[str, dict] = {}
    if row.firms_data:
        firms = list(row.firms_data)
        # Reconstruct persona set from firms_data so the metric tile
        # ("N search axes") still renders correctly.
        seen_personas: set[str] = set()
        for f in firms:
            for pid in f.get("_personas") or []:
                seen_personas.add(pid)
        persona_yamls = {pid: {} for pid in seen_personas}
    else:
        persona_yamls = _load_persona_yamls(row)
        firms = _aggregate_firms(persona_yamls)

    e = _html.escape

    started = row.created_at.strftime("%B %d, %Y") if row.created_at else "—"
    finished = row.completed_at.strftime("%B %d, %Y") if row.completed_at else None

    # Tier summary rows (top 10)
    summary_rows = []
    for f in firms[:10]:
        tier, tier_cls = _score_tier(f.get("confidence"))
        score = f.get("confidence")
        score_str = str(score) if score is not None else "—"
        loc_bits = [x for x in [f.get("city"), f.get("state")] if x]
        loc = ", ".join(loc_bits) if loc_bits else "—"
        n_axes = len(f.get("_personas") or [])
        cross = (
            f'<span class="cross-axis" title="Surfaced by {n_axes} different search axes — strongest match signal">×{n_axes}</span>'
            if n_axes >= 2
            else ""
        )
        anchor = _slug(f["name"])
        summary_rows.append(
            f'<tr class="row-{tier_cls}">'
            f'<td class="t-score"><span class="tier-pill {tier_cls}">{tier}</span><span class="num">{score_str}</span></td>'
            f'<td class="t-firm"><a href="#firm-{anchor}">{e(f["name"])}</a> {cross}</td>'
            f'<td class="t-loc">{e(loc)}</td>'
            f'<td class="t-fee">{_format_fee_range(f)}</td>'
            f"</tr>"
        )

    # Per-firm detail cards
    firm_cards: list[str] = []
    for f in firms:
        firm_cards.append(_render_firm_card(f, e))

    n_firms = len(firms)
    cross_count = sum(1 for f in firms if len(f.get("_personas") or []) >= 2)
    persona_count = len(persona_yamls)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lawyer search — {e(row.purpose)}</title>
<style>
{_REPORT_CSS}
</style>
</head>
<body>
<div class="page">
  <header class="cover">
    <div class="eyebrow">Professional search report</div>
    <h1>{e(row.purpose)}</h1>
    <div class="meta">
      <span>{e(row.vertical.replace("_", " ").title())}</span>
      <span class="dot">·</span>
      <span>{started}</span>
      {f'<span class="dot">·</span><span>finished {finished}</span>' if finished else ''}
    </div>
    <div class="metrics">
      <div class="metric"><div class="num">{n_firms}</div><div class="lbl">Firms</div></div>
      <div class="metric"><div class="num">{persona_count}</div><div class="lbl">Search axes</div></div>
      <div class="metric"><div class="num">{cross_count}</div><div class="lbl">Cross-axis matches</div></div>
    </div>
  </header>

  <section class="block">
    <h2>Tier summary</h2>
    <p class="lede">Top firms ranked by confidence. <span class="cross-axis-inline">×N</span> means a firm was independently surfaced by N different search axes — the strongest quality signal.</p>
    <table class="tier-table">
      <thead>
        <tr><th>Tier</th><th>Firm</th><th>Location</th><th>Estimated fees</th></tr>
      </thead>
      <tbody>
        {''.join(summary_rows) if summary_rows else '<tr><td colspan="4" class="empty">No firms surfaced.</td></tr>'}
      </tbody>
    </table>
  </section>

  <section class="block">
    <h2>How firms were ranked</h2>
    <p>Firms were scored 0–100 against externally-verifiable credentials only — Chambers USA / Global rankings, AILA elected leadership (not just membership), AV Preeminent and Best Lawyers peer recognition, ABIL membership, documented PACER filings, third-party press coverage, and government-service alumni status.</p>
    <p>Self-published marketing — firm blog posts, &ldquo;success stories&rdquo;, self-described practice pages — was excluded from weighting. Where a firm&rsquo;s own site is cited, it is for contact information only, never as a credential source.</p>
    <p>Three independent search axes were dispatched in parallel: <em>elite boutiques</em> (peer-recognized specialists), <em>startup-focused</em> (firms with published positions on the specific regulatory question), and <em>federal-court litigators</em> (counsel of record in reported decisions). Convergence across axes is treated as a quality signal and surfaced via the <span class="cross-axis-inline">×N</span> badge.</p>
  </section>

  <section class="block firm-list">
    <h2>Firm dossiers</h2>
    {''.join(firm_cards) if firm_cards else '<p class="empty">No firms surfaced.</p>'}
  </section>

  <section class="block brief">
    <h2>Case brief used for this search</h2>
    <pre>{e(row.case_brief.strip())}</pre>
  </section>

  <footer>
    <div>Generated {_dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")} by Guardian professional search · Report ID {e(row.id[:8])}</div>
    <div class="disclaimer">This report is research output, not legal advice. Verify each credential against its cited source before retaining a firm.</div>
  </footer>
</div>
</body>
</html>
"""
    return html


def _format_fee_range(f: dict) -> str:
    lo = f.get("petition_fee_low")
    hi = f.get("petition_fee_high") or lo
    if lo is None:
        return '<span class="fees-missing-inline">quote required</span>'
    if hi is None or hi == lo:
        return f"${int(lo):,}"
    return f"${int(lo):,}–${int(hi):,}"


def _render_firm_card(f: dict, e) -> str:
    name = f.get("name", "(unnamed)")
    anchor = _slug(name)
    score = f.get("confidence")
    tier, tier_cls = _score_tier(score)
    score_str = str(score) if score is not None else "—"

    contact_bits: list[str] = []
    if f.get("lead_attorney"):
        role = f.get("role")
        contact_bits.append(
            f"<strong>{e(f['lead_attorney'])}</strong>"
            + (f" <span class='role'>({e(role)})</span>" if role else "")
        )
    loc = ", ".join([x for x in [f.get("city"), f.get("state")] if x])
    if loc:
        contact_bits.append(e(loc))
    if f.get("phone"):
        contact_bits.append(e(f["phone"]))
    if f.get("email"):
        contact_bits.append(f'<a href="mailto:{e(f["email"])}">{e(f["email"])}</a>')
    if f.get("website"):
        contact_bits.append(f'<a href="{e(f["website"])}" target="_blank" rel="noopener">{e(f["website"].replace("https://", "").replace("http://", "").rstrip("/"))}</a>')

    fee_html = ""
    fee_rows: list[str] = []
    if f.get("consultation_fee_low") is not None:
        lo = f["consultation_fee_low"]
        hi = f.get("consultation_fee_high") or lo
        amt = f"${int(lo):,}" + (f"–${int(hi):,}" if hi != lo else "")
        fee_rows.append(f'<dt>Consultation</dt><dd>{amt}</dd>')
    if f.get("petition_fee_low") is not None:
        lo = f["petition_fee_low"]
        hi = f.get("petition_fee_high") or lo
        amt = f"${int(lo):,}" + (f"–${int(hi):,}" if hi != lo else "")
        label = f.get("service_fee_label", "Primary engagement")
        fee_rows.append(f'<dt>{e(label)}</dt><dd>{amt}</dd>')
    if not fee_rows:
        fee_rows.append(
            '<dt>Fees</dt><dd class="fees-missing">'
            'Not publicly disclosed — request quote at consultation</dd>'
        )
    basis = f.get("fee_basis")
    basis_html = (
        f'<div class="fee-basis">Source: {e(basis)}</div>' if basis else ""
    )
    fee_html = f'<dl class="fees">{"".join(fee_rows)}</dl>{basis_html}'

    why_fits = f.get("_why_fits") or []
    why_html = ""
    if len(why_fits) == 1:
        why_html = f"<p>{e(why_fits[0][1])}</p>"
    elif len(why_fits) > 1:
        why_html = "".join(
            f"<div class='persona-take'><div class='persona-tag'>{e(_persona_label(pid))}</div><p>{e(text)}</p></div>"
            for pid, text in why_fits
        )

    creds_html = ""
    if f.get("_credentials"):
        creds_html = (
            "<h4>Credentials <span class='note'>(externally verifiable)</span></h4>"
            "<ul class='creds'>"
            + "".join(f"<li>{e(c)}</li>" for c in f["_credentials"])
            + "</ul>"
        )

    lit_html = ""
    if f.get("litigation_capability"):
        lit_html = (
            f"<h4>Litigation capability</h4><p class='lit'>{e(f['litigation_capability'])}</p>"
        )

    risks_html = ""
    if f.get("_risks"):
        risks_html = (
            "<h4>Caveats</h4><ul class='risks'>"
            + "".join(f"<li>{e(r)}</li>" for r in f["_risks"])
            + "</ul>"
        )

    sources_html = ""
    if f.get("_sources"):
        sources_html = (
            "<h4>Verification sources</h4><ul class='sources'>"
            + "".join(
                f'<li><a href="{e(s)}" target="_blank" rel="noopener">{e(s)}</a></li>'
                for s in f["_sources"]
            )
            + "</ul>"
        )

    persona_pills = " ".join(
        f'<span class="persona-pill">{e(_persona_label(p))}</span>'
        for p in (f.get("_personas") or [])
    )
    n_axes = len(f.get("_personas") or [])
    cross_html = (
        f'<span class="cross-axis-card" title="Surfaced by {n_axes} different search axes">×{n_axes} cross-axis match</span>'
        if n_axes >= 2 else ""
    )

    return f"""
<article class="firm" id="firm-{anchor}">
  <div class="firm-head">
    <div class="firm-score">
      <span class="tier-pill {tier_cls}">{tier}</span>
      <span class="firm-score-num">{score_str}</span>
    </div>
    <div class="firm-title">
      <h3>{e(name)}</h3>
      <div class="firm-axes">{persona_pills} {cross_html}</div>
    </div>
  </div>
  <div class="firm-contact">{" · ".join(contact_bits)}</div>
  {fee_html}
  {why_html}
  {creds_html}
  {lit_html}
  {risks_html}
  {sources_html}
</article>
"""


_REPORT_CSS = """
:root {
  --ink: #0d1424;
  --muted: #556480;
  --muted-2: #7b8ba5;
  --hairline: #e4edf7;
  --soft: #f5f7fb;
  --card: #ffffff;
  --accent: #2f5bae;
  --accent-soft: #eaf2ff;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.55;
  color: var(--ink);
  background: linear-gradient(180deg, #edf3f9 0%, #f4f7fb 60%, #fbfcfe 100%);
  -webkit-font-smoothing: antialiased;
}
.page {
  max-width: 880px;
  margin: 48px auto;
  padding: 0 32px 64px;
}
header.cover {
  padding: 56px 0 40px;
  border-bottom: 1px solid var(--hairline);
}
.eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted-2);
}
header.cover h1 {
  margin: 14px 0 14px;
  font-family: "Charter", "Georgia", "Times New Roman", serif;
  font-size: 44px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.meta { color: var(--muted); font-size: 14px; }
.meta .dot { color: #c4cad6; margin: 0 8px; }
.metrics {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}
.metric {
  flex: 1;
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: 14px;
  padding: 16px 20px;
  box-shadow: 0 6px 20px rgba(56,85,131,0.04);
}
.metric .num {
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
}
.metric .lbl {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted-2);
  margin-top: 8px;
}
.block { margin-top: 56px; }
.block h2 {
  font-family: "Charter", "Georgia", "Times New Roman", serif;
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--ink);
}
.block .lede { color: var(--muted); margin: 0 0 20px; font-size: 14px; }
.block p { color: var(--muted); margin: 0 0 14px; max-width: 64ch; }
.block p strong, .block p em { color: var(--ink); font-style: normal; font-weight: 600; }

/* tier table */
.tier-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 6px 20px rgba(56,85,131,0.04);
}
.tier-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-2);
  background: var(--soft);
  padding: 12px 16px;
  border-bottom: 1px solid var(--hairline);
}
.tier-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--hairline);
  vertical-align: middle;
  font-size: 14px;
}
.tier-table tr:last-child td { border-bottom: 0; }
.tier-table .t-score { width: 100px; }
.tier-table .t-score .num { margin-left: 8px; color: var(--muted); font-variant-numeric: tabular-nums; font-size: 13px; }
.tier-table .t-firm a { color: var(--ink); font-weight: 600; text-decoration: none; }
.tier-table .t-firm a:hover { color: var(--accent); }
.tier-table .t-loc { color: var(--muted); }
.tier-table .t-fee { color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
.tier-table .empty { color: var(--muted-2); text-align: center; padding: 24px; }

/* tier pills */
.tier-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0;
  color: white;
}
.tier-pill.tier-s { background: #1f6f43; }
.tier-pill.tier-a { background: #2f5bae; }
.tier-pill.tier-b { background: #5b8dee; }
.tier-pill.tier-c { background: #9ba8c4; }
.tier-pill.tier-d { background: #c4cad6; color: #5a6478; }
.tier-pill.tier-unknown { background: #e4edf7; color: #7b8ba5; }

.cross-axis {
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: #fff6ea;
  color: #9c5a1c;
  border: 1px solid #ffe3c9;
  border-radius: 999px;
  vertical-align: middle;
}
.cross-axis-inline {
  display: inline-block;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 700;
  background: #fff6ea;
  color: #9c5a1c;
  border: 1px solid #ffe3c9;
  border-radius: 999px;
}

/* firm cards */
.firm {
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: 16px;
  padding: 28px 32px;
  margin-top: 16px;
  box-shadow: 0 6px 20px rgba(56,85,131,0.04);
}
.firm-head {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}
.firm-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 4px;
}
.firm-score .tier-pill {
  width: 40px;
  height: 40px;
  font-size: 17px;
  border-radius: 12px;
}
.firm-score-num {
  font-size: 13px;
  color: var(--muted-2);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.firm-title { flex: 1; min-width: 0; }
.firm-title h3 {
  margin: 0 0 6px;
  font-family: "Charter", "Georgia", "Times New Roman", serif;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}
.firm-axes { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.persona-pill {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  background: var(--soft);
  border: 1px solid var(--hairline);
  border-radius: 999px;
  padding: 3px 9px;
}
.cross-axis-card {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #9c5a1c;
  background: #fff6ea;
  border: 1px solid #ffe3c9;
  border-radius: 999px;
  padding: 3px 9px;
}

.firm-contact {
  margin-top: 14px;
  padding: 12px 14px;
  background: var(--soft);
  border-radius: 10px;
  font-size: 13.5px;
  color: var(--muted);
  line-height: 1.6;
}
.firm-contact strong { color: var(--ink); }
.firm-contact .role { color: var(--muted-2); font-weight: 400; }
.firm-contact a { color: var(--accent); text-decoration: none; }
.firm-contact a:hover { text-decoration: underline; }

.firm h4 {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted-2);
  margin: 22px 0 10px;
}
.firm h4 .note { font-weight: 500; text-transform: none; letter-spacing: 0; color: var(--muted-2); }
.firm p { color: var(--ink); font-size: 14.5px; margin: 0 0 12px; line-height: 1.65; }

.persona-take {
  position: relative;
  padding-left: 16px;
  margin-bottom: 16px;
}
.persona-take::before {
  content: '';
  position: absolute;
  left: 0; top: 4px; bottom: 4px;
  width: 3px;
  background: var(--accent);
  border-radius: 2px;
  opacity: 0.55;
}
.persona-take .persona-tag {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 4px;
}

dl.fees {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 6px 18px;
  margin: 16px 0 4px;
  padding: 14px 18px;
  background: var(--soft);
  border-radius: 10px;
  font-size: 13.5px;
}
dl.fees dt { color: var(--muted-2); font-weight: 600; }
dl.fees dd { margin: 0; color: var(--ink); font-variant-numeric: tabular-nums; }
dl.fees dd.fees-missing { color: var(--muted); font-style: italic; font-variant-numeric: normal; }
.fee-basis {
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted-2);
  font-style: italic;
}
.fees-missing-inline { color: var(--muted-2); font-style: italic; font-size: 12.5px; }

ul.creds, ul.risks, ul.sources {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 4px;
}
ul.creds li, ul.risks li, ul.sources li {
  position: relative;
  padding-left: 18px;
  font-size: 13.5px;
  color: var(--ink);
}
ul.creds li::before {
  content: '✓';
  position: absolute;
  left: 0; top: 0;
  color: #1f6f43;
  font-weight: 700;
}
ul.risks li {
  color: var(--muted);
}
ul.risks li::before {
  content: '!';
  position: absolute;
  left: 4px; top: 0;
  color: #9c5a1c;
  font-weight: 700;
}
ul.sources li::before {
  content: '↗';
  position: absolute;
  left: 0; top: 0;
  color: var(--muted-2);
}
ul.sources a {
  color: var(--accent);
  text-decoration: none;
  font-size: 12.5px;
  word-break: break-all;
}
ul.sources a:hover { text-decoration: underline; }
.firm p.lit { color: var(--muted); font-size: 13.5px; margin-bottom: 4px; }

.brief pre {
  background: var(--soft);
  border: 1px solid var(--hairline);
  border-radius: 12px;
  padding: 18px 22px;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--muted);
}

footer {
  margin-top: 64px;
  padding-top: 24px;
  border-top: 1px solid var(--hairline);
  font-size: 12px;
  color: var(--muted-2);
}
footer .disclaimer { margin-top: 6px; font-style: italic; }

@media (max-width: 640px) {
  .page { padding: 0 18px 48px; margin: 24px auto; }
  header.cover h1 { font-size: 32px; }
  .metrics { flex-direction: column; }
  .firm { padding: 22px; }
  .firm-head { flex-direction: row; }
}

@media print {
  body { background: white; }
  .page { margin: 0; max-width: none; padding: 0 24px; }
  header.cover { padding: 24px 0; }
  .firm, .metric, .tier-table { box-shadow: none; break-inside: avoid; }
  .block { margin-top: 32px; }
  a { color: var(--ink); }
  ul.sources a { color: var(--muted); }
}
"""


def _render_markdown(row: ProfessionalSearchRequestRow) -> str:
    """Render a portable markdown report of every firm surfaced.

    Reads the per-persona YAMLs that the runner saved (which carry the
    rich data — credentials, why_fit, sources, fees) and emits sections
    grouped by persona. Firms appearing in multiple personas are listed
    under each (with a note) — this is intentional, since the cross-axis
    overlap is itself a quality signal.
    """
    sections: list[str] = []

    sections.append(f"# Lawyer search — {row.purpose}")
    sections.append("")
    sections.append(f"**Vertical:** {row.vertical.replace('_', ' ')}  ")
    sections.append(f"**Started:** {row.created_at.isoformat() if row.created_at else '-'}  ")
    if row.completed_at:
        sections.append(f"**Finished:** {row.completed_at.isoformat()}  ")
    sections.append(f"**Status:** {row.status}")
    sections.append("")

    sections.append("## Case brief")
    sections.append("")
    sections.append("```")
    sections.append(row.case_brief.strip())
    sections.append("```")
    sections.append("")

    sections.append("## Methodology")
    sections.append("")
    sections.append(
        "Firms are scored 0–100 by externally-verifiable signals only — "
        "Chambers rankings, AILA elected leadership (not membership), "
        "AV Preeminent / Best Lawyers, ABIL membership, documented PACER "
        "filings, and third-party press. A firm's own marketing copy "
        "(blog posts, self-described practice pages) is excluded from "
        "weighting."
    )
    sections.append("")

    persona_status = row.persona_status or {}
    any_firms = False

    for persona_id, status in persona_status.items():
        title = persona_id.replace("_", " ").title()
        sections.append(f"## {title}")
        sections.append("")

        if status.get("status") != "complete":
            err = status.get("error") or "(no result)"
            sections.append(f"_Persona did not complete: {err}_")
            sections.append("")
            continue

        path_str = status.get("output_path")
        if not path_str:
            sections.append("_No output path recorded._")
            sections.append("")
            continue
        path = Path(path_str)
        if not path.exists():
            sections.append(f"_Output file missing on disk: `{path}`_")
            sections.append("")
            continue

        try:
            doc = _yaml.safe_load(path.read_text()) or {}
        except Exception as exc:
            sections.append(f"_Failed to read output file: {exc}_")
            sections.append("")
            continue

        firms = doc.get("firms") or []
        if not firms:
            sections.append("_No firms returned._")
            sections.append("")
            continue

        any_firms = True
        firms_sorted = sorted(firms, key=lambda f: -(f.get("confidence") or 0))

        for firm in firms_sorted:
            name = firm.get("name", "(unnamed)")
            score = firm.get("confidence")
            score_str = f" — score {score}" if score is not None else ""
            sections.append(f"### {name}{score_str}")
            sections.append("")

            # Contact line
            contact_bits = []
            if firm.get("lead_attorney"):
                role = firm.get("role")
                contact_bits.append(
                    f"**{firm['lead_attorney']}**" + (f" ({role})" if role else "")
                )
            loc = ", ".join([x for x in [firm.get("city"), firm.get("state")] if x])
            if loc:
                contact_bits.append(loc)
            if firm.get("phone"):
                contact_bits.append(firm["phone"])
            if firm.get("email"):
                contact_bits.append(firm["email"])
            if firm.get("website"):
                contact_bits.append(firm["website"])
            if contact_bits:
                sections.append(" · ".join(contact_bits))
                sections.append("")

            # Fees
            fee_lines = []
            if firm.get("consultation_fee_low") is not None:
                lo = firm["consultation_fee_low"]
                hi = firm.get("consultation_fee_high") or lo
                fee_lines.append(
                    f"- Consultation: ${lo:,.0f}"
                    + (f"–${hi:,.0f}" if hi != lo else "")
                )
            if firm.get("petition_fee_low") is not None:
                lo = firm["petition_fee_low"]
                hi = firm.get("petition_fee_high") or lo
                label = firm.get("service_fee_label", "Primary service")
                fee_lines.append(
                    f"- {label}: ${lo:,.0f}"
                    + (f"–${hi:,.0f}" if hi != lo else "")
                )
            if fee_lines:
                sections.append("**Fees**")
                sections.extend(fee_lines)
                sections.append("")

            if firm.get("why_fit"):
                sections.append("**Why this firm**")
                sections.append("")
                sections.append(firm["why_fit"].strip())
                sections.append("")

            creds = firm.get("credentials") or []
            if creds:
                sections.append("**Credentials (externally verifiable)**")
                for c in creds:
                    sections.append(f"- {c}")
                sections.append("")

            if firm.get("litigation_capability"):
                sections.append("**Litigation capability**")
                sections.append("")
                sections.append(firm["litigation_capability"].strip())
                sections.append("")

            risks = firm.get("risks") or []
            if risks:
                sections.append("**Risks / caveats**")
                for r in risks:
                    sections.append(f"- {r}")
                sections.append("")

            sources = firm.get("sources") or []
            if sources:
                sections.append("**Sources**")
                for s in sources:
                    sections.append(f"- <{s}>")
                sections.append("")

            sections.append("---")
            sections.append("")

    if not any_firms:
        sections.append("_No firms were ingested. Check per-persona errors above._")
        sections.append("")

    sections.append("")
    sections.append("_Generated by compliance-os professional search._")
    return "\n".join(sections)


@router.get("/{request_id}/download")
def download_search(
    request_id: str,
    format: str = "html",
    session: Session = Depends(get_session),
):
    """Render the full search result as a polished report.

    Two formats:
      - `html` (default): self-contained styled page, opens inline in
        the browser, prints cleanly to PDF. Firms are deduplicated
        across personas with rationales aggregated — one card per
        unique firm, cross-axis matches called out.
      - `md`: portable markdown, served as an attachment. Keeps the
        per-persona grouping for users who want to see each search
        axis separately.
    """
    row = session.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    if row.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Search not complete (status={row.status}); cannot download",
        )
    if row.paid_at is None:
        raise HTTPException(
            status_code=402,  # Payment Required — semantically correct
            detail="This report is locked. Unlock it for $15 via the checkout endpoint.",
        )

    safe_purpose = "".join(
        c if c.isalnum() or c in "-_" else "-" for c in row.purpose
    ).strip("-")[:60] or "report"

    # Bail early when there's nothing to render — applies to ALL formats
    # (md / html / pdf) so a stale row can't return a polished-but-empty
    # report in any guise. Must come before any format-specific branch.
    if not row.firms_data and not _load_persona_yamls(row):
        raise HTTPException(
            status_code=410,
            detail=(
                "This search's underlying firm data is no longer available "
                "(YAMLs missing and no DB-resident dossiers). Run a fresh "
                "search to regenerate the report."
            ),
        )

    if format == "md":
        body = _render_markdown(row)
        filename = f"lawyer-search-{safe_purpose}-{request_id[:8]}.md"
        return Response(
            content=body,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if format == "pdf":
        # Lazy import — WeasyPrint pulls in cairo/pango at import time.
        try:
            from weasyprint import HTML as _WeasyHTML
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="PDF rendering not available — server missing weasyprint",
            )
        html_body = _render_html(row)
        pdf_bytes = _WeasyHTML(string=html_body).write_pdf()
        filename = f"lawyer-search-{safe_purpose}-{request_id[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Default: polished HTML, inline so it opens as a page (not a download).
    body = _render_html(row)
    filename = f"lawyer-search-{safe_purpose}-{request_id[:8]}.html"
    return Response(
        content=body,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------------------------- Stripe paywall ----------------------------
#
# Pay-first model: anyone can pay (no account required). Stripe captures
# the email at checkout. Post-purchase, the user is sent to a success
# page with a "save this to your account" CTA — signing up there calls
# /claim, which links the search row to the new (or existing) user.


def _stripe():
    """Lazy-import + configure the Stripe SDK so the app boots without keys."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured — STRIPE_SECRET_KEY is not set",
        )
    import stripe as _s

    _s.api_key = settings.stripe_secret_key
    return _s


@router.post("/{request_id}/checkout")
def create_checkout_session(
    request_id: str,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None),
    session: Session = Depends(get_session),
):
    """Create a Stripe Checkout Session for a completed-but-unpaid search.

    Returns a JSON `{ url }` the client redirects to. The Checkout Session's
    `success_url` redirects back to `/find-lawyer/{id}/paid?session_id=...`,
    where the frontend polls until the webhook fires and `paid_at` is set.

    Pro free-pass: when the caller is an authenticated paid-Pro user and
    has not yet consumed their 1-search-per-period grant, we skip Stripe
    entirely — mark the row paid with `pro_free_grant_at` set, and return
    a direct redirect to the /paid page.
    """
    row = session.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    if row.status != "complete":
        raise HTTPException(
            status_code=409, detail=f"Search not complete (status={row.status})"
        )
    if row.paid_at is not None:
        return {"url": f"{settings.public_app_url}/find-lawyer/{request_id}/paid"}

    # Pro free-search short-circuit. Anonymous callers fall through to the
    # paid Stripe flow below — quietly, no error. We only consult auth
    # when a token is present so this endpoint stays open to logged-out
    # users (the dominant pre-signup flow).
    if authorization:
        try:
            payload = get_bearer_payload(authorization, session)
            user = session.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
        except HTTPException:
            user = None  # bad/expired token → just fall through to paid path
        if user is not None:
            from compliance_os.web.services.subscription_service import (
                get_pro_search_quota,
            )

            # Includes pro_trial users now — see subscription_service
            # `get_pro_search_quota` for the entitlement rule.
            pro_quota = get_pro_search_quota(user, session)
            if pro_quota.has_free_search:
                    now = _dt.datetime.utcnow()
                    row.paid_at = now
                    row.pro_free_grant_at = now
                    row.user_id = user.id
                    if not row.stripe_customer_email:
                        row.stripe_customer_email = user.email
                    session.commit()
                    logger.info(
                        "pro_free_grant: user %s consumed free search for %s",
                        user.id,
                        request_id,
                    )
                    return {
                        "url": f"{settings.public_app_url}/find-lawyer/{request_id}/paid",
                        "pro_free_grant": True,
                    }

    stripe = _stripe()
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            # Force a Stripe Customer for every $15 purchase so we can
            # later create a Pro trial subscription that bills the saved
            # card without re-prompting (see /start-pro-trial below).
            customer_creation="always",
            # Save the payment method to the customer so off-session
            # subscription creation can charge it after the trial ends.
            payment_intent_data={"setup_future_usage": "off_session"},
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Guardian — {row.purpose}",
                            "description": (
                                "Full lawyer search report (PDF + HTML) with all "
                                "firm dossiers, credentials, and verification sources."
                            ),
                        },
                        "unit_amount": settings.stripe_report_price_cents,
                    },
                    "quantity": 1,
                }
            ],
            # The session_id placeholder is filled in by Stripe before redirect.
            success_url=(
                f"{settings.public_app_url}/find-lawyer/{request_id}/paid"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{settings.public_app_url}/find-lawyer/{request_id}",
            client_reference_id=request_id,
            metadata={"professional_search_id": request_id},
            # Capture an email so we can pre-fill signup post-purchase.
            customer_email=None,  # let Stripe collect — pre-filling requires we have it
        )
    except Exception as exc:
        logger.exception("stripe checkout creation failed for %s", request_id)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}")

    # Optimistic write — webhook is the source of truth, but recording the
    # session id here lets us recover if the webhook ever lags.
    row.stripe_session_id = checkout.id

    # Stage 2 dispatch — fire enrichment as a background task IFF we have
    # firms_data to enrich AND we haven't already kicked off enrichment.
    # This runs in parallel with the user's Stripe session; by the time
    # they finish entering card details (~30-60s), enrichment is usually
    # 1/3 done. The /paid page polls /enrichment-status to update the UI
    # when it lands. Idempotent: re-clicks don't re-dispatch.
    if (
        row.firms_data
        and (row.enrichment_status or "idle") in ("idle", "failed")
    ):
        from compliance_os.web.services.enrichment_runner import run_enrichment_sync

        row.enrichment_status = "enriching"
        row.enrichment_started_at = _dt.datetime.utcnow()
        row.enrichment_error = None
        background_tasks.add_task(run_enrichment_sync, row.id)
        logger.info(
            "checkout: dispatched enrichment for %s (firms=%d)",
            request_id, len(row.firms_data),
        )

    session.commit()
    return {"url": checkout.url, "session_id": checkout.id}


@router.get(
    "/{request_id}/enrichment-status",
    response_model=EnrichmentStatusResponse,
)
def get_enrichment_status(
    request_id: str,
    session: Session = Depends(get_session),
):
    """Lightweight polling endpoint for the /paid page.

    Returns just the enrichment lifecycle state + a per-firm completion
    counter so the UI can render a "X of Y firms enriched" progress hint
    during the ~2-3min enrichment window. Avoids dragging the full
    firms_data + tier_report payload across the wire on every poll.
    """
    row = session.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")

    firms_total = len(row.firms_data or [])
    firms_enriched = sum(
        1
        for f in (row.firms_data or [])
        if isinstance(f, dict) and f.get("_enriched_at")
    )
    return EnrichmentStatusResponse(
        status=row.enrichment_status or "idle",
        started_at=(
            row.enrichment_started_at.isoformat()
            if row.enrichment_started_at else None
        ),
        completed_at=(
            row.enrichment_completed_at.isoformat()
            if row.enrichment_completed_at else None
        ),
        error=row.enrichment_error,
        firms_enriched=firms_enriched,
        firms_total=firms_total,
    )


@router.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_session),
):
    """Handle `checkout.session.completed` — the canonical 'paid' signal.

    Verified via `STRIPE_WEBHOOK_SECRET`. Idempotent: re-deliveries that
    re-process the same session are a no-op.
    """
    payload = await request.body()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    stripe = _stripe()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except Exception as exc:
        logger.warning("stripe webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}")

    event_type = event["type"]

    # Coerce StripeObject → plain dict. Newer stripe-python versions do NOT
    # have StripeObject inherit from dict, so sess.get(...) raises
    # AttributeError: get. to_dict_recursive() walks nested objects too,
    # so (sess.get("customer_details") or {}).get("email") works as expected.
    raw_obj = event["data"]["object"]
    if hasattr(raw_obj, "to_dict_recursive"):
        obj = raw_obj.to_dict_recursive()
    else:
        try:
            obj = dict(raw_obj)
        except Exception:
            obj = raw_obj  # last-ditch fallback; .get may still fail

    # Subscription lifecycle events — drive the SubscriptionRow mirror.
    # Note: customer.subscription.created arrives near-simultaneously with
    # checkout.session.completed (mode=subscription); both can create the
    # row, so the upsert helper is idempotent.
    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        _handle_subscription_event(event_type, obj, db)
        return {"received": True, "kind": "subscription_event", "type": event_type}

    if event_type != "checkout.session.completed":
        return {"received": True, "ignored": event_type}

    # Branch on Checkout mode: subscription signup vs. one-time payment.
    if obj.get("mode") == "subscription":
        _handle_subscription_checkout_completed(obj, db, stripe)
        return {"received": True, "kind": "subscription_checkout_completed"}

    # One-time payment → existing lawyer-search flow. The variable is
    # named `sess` from here for git-blame stability with the historical
    # implementation below.
    sess = obj

    request_id = sess.get("client_reference_id") or (sess.get("metadata") or {}).get(
        "professional_search_id"
    )
    if not request_id:
        # Operational red flag — every checkout we create sets this. If
        # we receive a verified webhook without it, either someone is
        # creating Sessions outside our flow against the same account,
        # or our own create_checkout_session call dropped client_reference_id.
        logger.error(
            "STRIPE_WEBHOOK_ALERT: verified checkout.session.completed with no "
            "client_reference_id and no metadata.professional_search_id. "
            "session_id=%s amount_total=%s customer_email=%s",
            sess.get("id"),
            sess.get("amount_total"),
            (sess.get("customer_details") or {}).get("email"),
        )
        return {"received": True, "ignored": "no client_reference_id"}

    row = db.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        # The row was deleted between checkout and webhook delivery (rare —
        # we don't currently delete rows). Log structured so we can grep
        # alerts; refunds may be needed if the customer was actually charged.
        logger.error(
            "STRIPE_WEBHOOK_ALERT: webhook for non-existent search row. "
            "request_id=%s session_id=%s amount_total=%s customer_email=%s",
            request_id,
            sess.get("id"),
            sess.get("amount_total"),
            (sess.get("customer_details") or {}).get("email"),
        )
        return {"received": True, "ignored": "unknown row"}

    if row.paid_at is not None:
        # Idempotency — Stripe retries successful webhooks if our 2xx is missed.
        return {"received": True, "already_paid": True}

    row.paid_at = _dt.datetime.utcnow()
    row.stripe_session_id = sess.get("id")
    customer_email = (sess.get("customer_details") or {}).get("email") or sess.get(
        "customer_email"
    )
    if customer_email:
        row.stripe_customer_email = customer_email

        # If a user with that email already exists, link the search now —
        # saves a step in the post-purchase signup flow.
        existing = (
            db.query(UserRow).filter(UserRow.email == customer_email).first()
        )
        if existing is not None and row.user_id is None:
            row.user_id = existing.id

    # If the commit fails AFTER Stripe has already charged the customer,
    # the user is in the worst state: they paid but our DB never reflects
    # it. Stripe will retry the webhook, but if the failure is persistent
    # (constraint violation, schema drift), every retry will fail. Log
    # an explicit ALERT so we catch it in observability and can manually
    # reconcile (mark paid_at by hand, or refund). The HTTP 500 we then
    # return causes Stripe to retry — preserving the canonical recovery
    # path for transient failures.
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "STRIPE_WEBHOOK_ALERT: db.commit failed AFTER customer was charged. "
            "request_id=%s session_id=%s amount_total=%s customer_email=%s exc=%s",
            request_id,
            sess.get("id"),
            sess.get("amount_total"),
            customer_email,
            exc,
        )
        # Re-raise so Stripe sees a 5xx and retries. If the failure is
        # transient the next retry succeeds; if persistent we'll have
        # the alert log + the original Stripe charge to manually resolve.
        raise HTTPException(status_code=500, detail="commit failed; will retry")
    logger.info("stripe webhook: marked search %s paid", request_id)

    # NOTE: trials are no longer silently auto-created on $15 payment.
    # With saved-card now in place (`setup_future_usage`), an auto-attach
    # would mean a surprise $20/mo charge after 30 days — exactly the
    # negative-option pattern we want to avoid. Trial creation now flows
    # through the explicit "Start Pro free for 30 days" CTA on the paid
    # page → POST /{request_id}/start-pro-trial.

    return {"received": True, "paid": True}


# ---------------------------- Subscription helpers ----------------------------


def _to_dt_or_none(epoch: int | None) -> _dt.datetime | None:
    if not epoch:
        return None
    return _dt.datetime.utcfromtimestamp(int(epoch))


def _upsert_subscription_from_stripe(
    sub_obj: dict,
    user_id: str | None,
    db: Session,
) -> "SubscriptionRow | None":
    """Mirror a Stripe Subscription object into our subscriptions table.

    Idempotent — keyed on stripe_subscription_id. Returns the row, or
    None if we cannot resolve a user_id (orphan subscription — log and
    skip rather than create rows we can't attribute).
    """
    from compliance_os.web.models.auth import SubscriptionRow as _SubRow
    from compliance_os.web.services.subscription_service import derive_tier

    sub_id = sub_obj.get("id")
    if not sub_id:
        logger.error("STRIPE_WEBHOOK_ALERT: subscription event with no id")
        return None

    row = (
        db.query(_SubRow)
        .filter(_SubRow.stripe_subscription_id == sub_id)
        .first()
    )

    # Resolve user_id — prefer caller-supplied, then metadata.user_id on
    # the sub itself. If neither, the row is unattributable.
    if user_id is None:
        meta = sub_obj.get("metadata") or {}
        user_id = meta.get("user_id")
    if user_id is None and row is not None:
        user_id = row.user_id  # already known from earlier event
    if user_id is None:
        logger.error(
            "STRIPE_WEBHOOK_ALERT: subscription %s has no resolvable user_id "
            "(no metadata.user_id, no existing row). Skipping.",
            sub_id,
        )
        return None

    status = sub_obj.get("status") or "incomplete"
    is_canceled = status in ("canceled", "incomplete_expired", "unpaid")
    new_values = {
        "user_id": user_id,
        "stripe_customer_id": sub_obj.get("customer"),
        "stripe_subscription_id": sub_id,
        "stripe_price_id": _extract_price_id(sub_obj),
        "status": status,
        "tier": derive_tier(status),
        "current_period_start": _to_dt_or_none(sub_obj.get("current_period_start")),
        "current_period_end": _to_dt_or_none(sub_obj.get("current_period_end")),
        "trial_end": _to_dt_or_none(sub_obj.get("trial_end")),
        "cancel_at_period_end": bool(sub_obj.get("cancel_at_period_end")),
        "canceled_at": (
            _to_dt_or_none(sub_obj.get("canceled_at"))
            if is_canceled
            else None
        ),
    }

    if row is None:
        row = _SubRow(**new_values)
        db.add(row)
    else:
        for k, v in new_values.items():
            setattr(row, k, v)
    return row


def _extract_price_id(sub_obj: dict) -> str | None:
    """Pull the first price id off a Stripe Subscription object.

    Subscriptions support multiple line items in theory, but our Pro
    product is a single price. Defensive: return None if shape changes.
    """
    items = (sub_obj.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price") or {}
    return price.get("id")


def _handle_subscription_event(event_type: str, sub_obj: dict, db: Session) -> None:
    """customer.subscription.{created,updated,deleted} → upsert mirror row."""
    row = _upsert_subscription_from_stripe(sub_obj, user_id=None, db=db)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "STRIPE_WEBHOOK_ALERT: subscription %s commit failed for %s",
            event_type,
            sub_obj.get("id"),
        )
        raise HTTPException(status_code=500, detail="commit failed; will retry")
    if row is not None:
        logger.info(
            "stripe webhook: subscription %s %s tier=%s status=%s",
            row.stripe_subscription_id,
            event_type,
            row.tier,
            row.status,
        )


def _handle_subscription_checkout_completed(sess: dict, db: Session, stripe) -> None:
    """checkout.session.completed for mode=subscription.

    Stripe also fires customer.subscription.created at the same time, so
    most of the time the SubscriptionRow is already in place by the time
    this handler runs. But ordering is not guaranteed, so we fetch the
    Subscription and upsert defensively.
    """
    sub_id = sess.get("subscription")
    if not sub_id:
        logger.error(
            "STRIPE_WEBHOOK_ALERT: subscription checkout %s has no subscription id",
            sess.get("id"),
        )
        return

    user_id = sess.get("client_reference_id") or (sess.get("metadata") or {}).get("user_id")
    try:
        full = stripe.Subscription.retrieve(sub_id)
        sub_obj = (
            full.to_dict_recursive() if hasattr(full, "to_dict_recursive") else dict(full)
        )
    except Exception:
        logger.exception(
            "STRIPE_WEBHOOK_ALERT: failed to fetch subscription %s", sub_id
        )
        return

    _upsert_subscription_from_stripe(sub_obj, user_id, db)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "STRIPE_WEBHOOK_ALERT: subscription_checkout commit failed for %s", sub_id
        )
        raise HTTPException(status_code=500, detail="commit failed; will retry")


def _maybe_attach_trial(
    user: UserRow,
    db: Session,
    *,
    stripe,
    customer_id: str | None,
    source: str,
) -> None:
    """Create a 30-day Pro trial for `user` if they don't already have one.

    No-op if:
      * user already has any active subscription (paid or trialing)
      * STRIPE_PRO_PRICE_ID is not configured (graceful skip — the trial
        is a benefit, not a payment, so missing config shouldn't crash
        the calling search-payment flow)

    Stripe will fire customer.subscription.created back to our webhook,
    which is what actually persists the SubscriptionRow. This function
    just initiates the Stripe-side state.
    """
    from compliance_os.web.services.subscription_service import get_active_subscription

    if not settings.stripe_pro_price_id:
        return  # Pro not configured — skip trial creation.
    if get_active_subscription(user, db) is not None:
        return  # Already entitled.

    # Resolve a Stripe Customer for this user — reuse the one from the
    # one-time charge if present, otherwise create one keyed by email.
    if not customer_id:
        try:
            c = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id},
            )
            customer_id = c.id if hasattr(c, "id") else c.get("id")
        except Exception:
            logger.exception(
                "trial attach: failed to create Stripe customer for %s", user.id
            )
            return

    trial_end = int(
        (_dt.datetime.utcnow() + _dt.timedelta(days=30)).timestamp()
    )
    try:
        stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": settings.stripe_pro_price_id}],
            trial_end=trial_end,
            # If the user never adds a card during the trial, Stripe will
            # cancel the sub at trial_end rather than fail to charge.
            trial_settings={"end_behavior": {"missing_payment_method": "cancel"}},
            payment_settings={"save_default_payment_method": "on_subscription"},
            metadata={
                "user_id": user.id,
                "trial_source": source,
            },
        )
    except Exception:
        logger.exception(
            "trial attach: Stripe.Subscription.create failed for user %s", user.id
        )
        return
    logger.info("trial attach: 30-day Pro trial created for user %s (source=%s)",
                user.id, source)


@router.post("/{request_id}/start-pro-trial")
def start_pro_trial(
    request_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Opt-in: start a 30-day Pro trial that auto-renews at \$20/mo.

    Called from the paid page's "Keep Pro free for 30 days" CTA. The
    user has just paid \$15 for a one-off search — that checkout saved
    their card via `setup_future_usage`. We use that saved card to
    create a Stripe subscription with a 30-day trial; Stripe auto-bills
    the standard Pro price (\$20/mo) at trial end unless the user
    cancels via the billing portal.

    Idempotent: if the user already has any active subscription
    (paid or trialing), returns ok without creating a duplicate.
    """
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    row = db.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    if row.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="This search isn't claimed under your account.",
        )
    if row.paid_at is None or not row.stripe_session_id:
        raise HTTPException(
            status_code=409,
            detail="Need a paid one-off search before starting a Pro trial.",
        )

    from compliance_os.web.services.subscription_service import get_active_subscription
    if get_active_subscription(user, db) is not None:
        return {"ok": True, "already_active": True}

    if not settings.stripe_pro_price_id:
        raise HTTPException(
            status_code=503,
            detail="Pro plan not configured on server (STRIPE_PRO_PRICE_ID).",
        )

    stripe = _stripe()

    # Pull the saved Stripe Customer + payment method from the $15 payment.
    # Sessions older than the setup_future_usage change won't have a saved
    # card; in that case we surface a clear error so the UI can fall back
    # to the standard /api/subscription/checkout flow (re-enter card).
    try:
        sess = stripe.checkout.Session.retrieve(
            row.stripe_session_id,
            expand=["payment_intent.payment_method"],
        )
    except Exception as exc:
        logger.exception("stripe session retrieve failed for %s", request_id)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}")

    customer_id = (
        sess.get("customer") if isinstance(sess, dict) else getattr(sess, "customer", None)
    )
    if not customer_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "No saved card on this purchase — start a Pro subscription via "
                "/pricing instead (you'll re-enter card details)."
            ),
        )

    _maybe_attach_trial(
        user,
        db,
        stripe=stripe,
        customer_id=customer_id,
        source="post_search_cta",
    )

    return {
        "ok": True,
        "trial_days": 30,
        "renewal_price_cents": 2000,  # informational — actual amount comes from Stripe price
    }


@router.post("/{request_id}/claim", response_model=SearchResponse)
def claim_search(
    request_id: str,
    authorization: str | None = Header(None),
    db: Session = Depends(get_session),
):
    """Link a paid search row to the authenticated user.

    Used after pay-first checkout: user signs up (or logs in), then their
    client calls this with their bearer token. The row's `user_id` is set,
    making it appear under "My searches" in the dashboard.
    """
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    row = db.get(ProfessionalSearchRequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Search request not found")
    if row.paid_at is None:
        raise HTTPException(
            status_code=402,
            detail="Cannot claim an unpaid search — complete checkout first.",
        )

    # If already claimed by this same user, treat as idempotent success.
    # If claimed by SOMEONE ELSE, reject — even with a valid token.
    if row.user_id is not None and row.user_id != user.id:
        raise HTTPException(
            status_code=409,
            detail="This search has already been claimed by another account.",
        )

    # Defense-in-depth: require the claimer's email to match the email
    # Stripe captured at checkout. UUIDs are unguessable but the search
    # status URL is shareable, and a Referer leak or screenshot would
    # otherwise let any authed account claim a stranger's paid search.
    # Only enforce when Stripe gave us an email (older rows may be null).
    if (
        row.stripe_customer_email
        and row.stripe_customer_email.strip().lower() != (user.email or "").strip().lower()
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Email mismatch: this search was paid for by a different "
                "email. Sign in (or sign up) with the email you used at "
                "checkout to claim it."
            ),
        )

    row.user_id = user.id

    # Skip-onboarding shortcut: if the search came with a substantive
    # brief or supporting docs and isn't already case-attached, mint a
    # case for it now. The user will be redirected straight to the case
    # page (post-claim flow) instead of being forced through the empty
    # discovery wizard. They can always fill the wizard later for richer
    # follow-ups — it remains available, just not blocking.
    #
    # Threshold rationale: 400 chars is "above the 200-char minimum + a
    # bit more than the floor", which signals real intent. Any uploaded
    # files are an even stronger signal — the user already gathered
    # documents, so they clearly know their situation.
    BRIEF_RICHNESS_CHARS = 400
    has_uploads = bool((row.uploaded_notes or "").strip())
    brief_is_rich = (
        len((row.case_brief or "").strip()) >= BRIEF_RICHNESS_CHARS
        or has_uploads
    )
    if row.case_id is None and brief_is_rich:
        from compliance_os.web.models.tables import CaseRow as _CaseRow

        # Map vertical → workflow_type so the case shows the right track
        # in dashboards and CTAs. Verticals without a clear track default
        # to immigration (the most common path through find-lawyer).
        _VERTICAL_TO_WORKFLOW = {
            "immigration_attorney": "immigration",
            "immigration_eb5": "immigration",
            "tax_attorney": "tax",
            "cpa": "tax",
            "caa": "tax",
            "corporate_attorney": "corporate",
            "bank": "",
        }
        case = _CaseRow(
            user_id=user.id,
            workflow_type=_VERTICAL_TO_WORKFLOW.get(row.vertical, "immigration"),
            # `status="discovery"` is the default. Leave it — if the user
            # opens the discovery wizard later it picks up correctly.
        )
        db.add(case)
        db.flush()  # need case.id before assigning back
        row.case_id = case.id
        logger.info(
            "claim auto-created case %s for search %s (brief=%dch uploads=%s)",
            case.id, request_id, len((row.case_brief or "").strip()), has_uploads,
        )

    db.commit()
    db.refresh(row)

    # Trial creation is no longer auto-attached on claim. Users opt in
    # via the explicit "Start Pro free for 30 days" CTA on the paid page,
    # which calls POST /{request_id}/start-pro-trial. Keeps the claim
    # action transactionally simple (just links search → user) and
    # avoids any surprise auto-billing once the saved card lands.

    # Caller is now the authenticated owner — return full PII.
    return _serialize(row, include_pii=True)


# NOTE: `GET /mine/list` is defined above near the top of the router
# (next to `GET /{request_id}`) so the static-prefix route appears
# before the catch-all in declaration order. The duplicate that used
# to live here was removed during the code-review fixes.
