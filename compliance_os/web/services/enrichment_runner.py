"""Stage 2 per-firm enrichment runner.

Triggered by a user clicking "Unlock for $15" on the search-results
page, NOT by Stripe webhook confirmation. The dispatch fires in the
checkout endpoint right before returning the Stripe URL — so enrichment
runs in parallel with the user's ~30-60s card-entry window, hiding the
2-3 minute latency.

What enrichment does (per firm in `row.firms_data`):
  * Verifies the firm's lead_attorney's INDIVIDUAL Chambers / Legal500 /
    Best Lawyers band — distinct from the firm's band. The two diverge
    frequently (Foster LLP firm Band 1 / Loughran personal Band 4 was
    the incident that motivated this).
  * Lists 2-3 alternate attorneys at the same firm whose individual
    profile fits the case better, with their bands. Used by the
    intake-template UI to suggest who to actually request.
  * Verifies each existing source URL still resolves and matches its
    described content.
  * Flags routing risk when firm_band - lead_attorney_band >= 2.

Output is merged back into `firms_data` under underscore-prefixed keys
(`_lead_attorney_band`, `_lead_attorney_credentials`,
`_alternate_attorneys`, `_verified_sources`, `_individual_band_gap`)
mirroring the existing `_personas` / `_why_fits` convention.

Failure isolation: per-firm tasks run via asyncio.gather with
return_exceptions=True. One firm's failure produces a
`_enrichment_error` on that firm's dict; other firms commit normally.
The row's `enrichment_status` flips to `complete` even with partial
failures so the UI can render what we have. Only catastrophic failures
(no firms at all, runner crash) flip to `failed`.

Self-heal: if the runner is SIGTERM'd mid-execution, the row stays
`enrichment_status=enriching` past `enrichment_started_at + 10min`.
The boot-time reaper in search_reaper.py picks it up and re-dispatches.
Re-runs are idempotent because we overwrite the same underscore-prefixed
keys.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import re
from typing import Any

import anthropic
import httpx
from sqlalchemy.orm import Session

from compliance_os.settings import settings
from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables import ProfessionalSearchRequestRow

logger = logging.getLogger(__name__)


# Cheaper model for enrichment than the persona discovery pass — we're
# not generating a tier list here, just verifying specific facts about
# named people. Haiku 4.5 with web_search hits the right $/quality knee.
ENRICHMENT_MODEL = "claude-haiku-4-5-20251001"

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}

# Per-firm wall-clock cap. Each firm task does 4-6 web_search calls plus
# a synthesis turn. 4 minutes is generous for the slow-Anthropic edge case.
PER_FIRM_TIMEOUT_S = 240

# Hard cap on parallel firm enrichments. Anthropic rate-limits at the
# org level; we don't want one search hammering the limit and starving
# concurrent searches. 6 in parallel keeps us under the rate ceiling
# even with 3 concurrent searches running.
MAX_CONCURRENCY = 6

# Soft retry on pause_turn. Each pause_turn means web_search hit its
# server-side cap (10 calls per turn) but the model wants more. We
# allow one extra turn for stubborn lookups.
MAX_PAUSE_TURN_RETRIES = 1

# Band-gap threshold for the routing-risk warning. Chambers bands are
# 1 (best) → 5+. A 2-tier gap between firm and individual (e.g. firm
# Band 1, lead Band 3) is the threshold above which we tell the user
# "the named partner you're booking is materially below the firm's
# headline credential."
BAND_GAP_WARN_THRESHOLD = 2


# ---------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are verifying credentials for ONE law firm in a paid lawyer-search report.
The user paid $15 to unlock the deeper diligence layer; your job is to give
them the per-attorney verification they couldn't get pre-payment.

# The firm
- Firm name: {firm_name}
- City / State: {city}, {state}
- Lead attorney listed: {lead_attorney}
- Existing firm-level credentials (do NOT repeat these — verify the *individual*):
{firm_credentials_block}
- Existing source URLs (verify each one is real and matches its description):
{firm_sources_block}

# Case context (so you know which attorney specialty fits)
{case_purpose}

{case_brief_block}

# Your task — output a single JSON object inside ```json fences

Use web_search aggressively. Look up:

1. The lead_attorney's INDIVIDUAL Chambers USA / Chambers Global / Legal500 /
   Best Lawyers profile. Find their personal band ranking, NOT the firm's.
   Common URLs to check:
   - chambers.com/lawyer/<slug>
   - chambers.com/profile/<slug>
   - legal500.com/c/<region>/<practice>/<lawyer-slug>
   - bestlawyers.com/lawyers/<slug>

2. Their actual practice focus from the firm's bio page. EB-5 attorneys
   often DON'T do H-1B owner-beneficiary cases well, and vice versa.

3. Whether the existing source URLs above are still live and match their
   described content. If a source 404s or describes something else, flag it.

4. 2-3 alternate attorneys at the SAME firm whose individual profile fits
   THIS case better than the lead_attorney. Skip founding partners who only
   take retained matters > $500K (mark them `takes_outside_consults: false`).

# Output schema (REQUIRED — output exactly this shape inside ```json fences)

```json
{{
  "lead_attorney_band": 4,
  "lead_attorney_band_source": "Chambers USA",
  "lead_attorney_band_year": 2025,
  "lead_attorney_practice_focus": "EB-5 / L-1 / E-2 / UHNW investor immigration",
  "lead_attorney_credentials": [
    "Chambers USA Band 4 — Texas Immigration (2025)",
    "AILA — past Texas Chapter Chair"
  ],
  "lead_attorney_takes_outside_consults": true,
  "individual_vs_firm_band_gap_warning": "Firm Band 1, lead attorney Band 4 — 3-tier gap. Routing risk: book may go to associate.",
  "alternate_attorneys": [
    {{
      "name": "Charles Foster",
      "band": 1,
      "band_source": "Chambers USA",
      "practice_focus": "Business immigration generalist; H-1B, L-1, EB-1/2/3",
      "fit_for_case": "Direct match: handles H-1B owner-beneficiary regularly.",
      "takes_outside_consults": false,
      "consult_routing_note": "Founding partner; only on retained matters."
    }},
    {{
      "name": "Helene Dang",
      "band": 2,
      "band_source": "Chambers USA",
      "practice_focus": "Employment-based immigration head, Houston office",
      "fit_for_case": "Strong H-1B specialty-occupation track record.",
      "takes_outside_consults": true,
      "consult_routing_note": "Standard intake."
    }}
  ],
  "verified_sources": [
    {{
      "url": "https://...",
      "verified": true,
      "title": "Robert F. Loughran — Foster LLP",
      "note": "Live; matches lead_attorney bio."
    }}
  ],
  "rfe_pattern": null
}}
```

Output rules (these are non-negotiable):

* `lead_attorney_band` MUST be the **named individual's** band, NOT the firm's.
  If you can't find an individual profile, set `lead_attorney_band: null` and
  put `"profile not found"` in `lead_attorney_band_source`.

* `individual_vs_firm_band_gap_warning` is a string when there's a
  meaningful gap (≥2 tiers) and `null` otherwise. Do NOT manufacture a
  warning when there isn't one.

* `alternate_attorneys` must be SAME-FIRM partners. Don't suggest people
  at other firms. List 2-3, sorted by case-fit (best first).

* `verified_sources` covers EACH source URL from the input list, in order.
  Mark `verified: false` if 404 / mismatched / unreachable.

* `rfe_pattern` is a one-paragraph summary if you find published RFE
  patterns (Cap-Gap, specialty-occupation, employer-employee, etc.) the
  attorney has dealt with. Most of the time this will be `null` — that's fine.

* If you can't find good info, return `null` for the field rather than
  inventing. The user paid for verification, not speculation.

* Output ONLY the JSON object inside ```json fences. No prose before or
  after.
"""


def _format_firm_block(firm: dict[str, Any]) -> tuple[str, str, str]:
    """Pull the firm's existing credentials/sources into prompt-ready text."""
    creds = firm.get("_credentials") or firm.get("credentials") or []
    sources = firm.get("_sources") or firm.get("sources") or []
    case_brief = firm.get("_case_brief", "")

    creds_block = "\n".join(f"  - {c}" for c in creds[:5]) or "  (none listed)"
    sources_block = "\n".join(f"  - {s}" for s in sources[:5]) or "  (none listed)"
    case_brief_block = (
        f"# Case brief excerpt\n{case_brief.strip()[:1200]}"
        if case_brief.strip()
        else ""
    )
    return creds_block, sources_block, case_brief_block


def _build_prompt(firm: dict[str, Any], purpose: str, case_brief: str) -> str:
    creds_block, sources_block, case_brief_block = _format_firm_block(
        {**firm, "_case_brief": case_brief}
    )
    return _PROMPT_TEMPLATE.format(
        firm_name=firm.get("name", "(unknown)"),
        city=firm.get("city") or "—",
        state=firm.get("state") or "—",
        lead_attorney=firm.get("lead_attorney") or "(not specified)",
        firm_credentials_block=creds_block,
        firm_sources_block=sources_block,
        case_purpose=purpose,
        case_brief_block=case_brief_block,
    )


# ---------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """Pull the JSON object out of the model's response. None on parse fail."""
    match = _JSON_FENCE_RE.search(text)
    if not match:
        # Sometimes the model omits fences — try a bare JSON parse on the
        # whole response as a fallback. Won't catch trailing prose, but
        # better than dropping the result.
        try:
            return json.loads(text.strip())
        except Exception:
            return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


# ---------------------------------------------------------------------
# Per-firm task
# ---------------------------------------------------------------------

async def _enrich_one_firm(
    client: anthropic.AsyncAnthropic,
    firm: dict[str, Any],
    *,
    purpose: str,
    case_brief: str,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    """Run one firm's enrichment. Returns the enrichment dict (or error dict)."""
    firm_name = firm.get("name", "(unknown)")
    async with sem:
        prompt = _build_prompt(firm, purpose, case_brief)
        messages: list[dict] = [{"role": "user", "content": prompt}]
        retries = 0
        try:
            while True:
                logger.info(
                    "enrich firm '%s': stream open (retry=%d)",
                    firm_name, retries,
                )
                async with client.messages.stream(
                    model=ENRICHMENT_MODEL,
                    max_tokens=4096,
                    system=(
                        "You are a credential-verification specialist for a "
                        "lawyer-search service. Output strict JSON only."
                    ),
                    tools=[WEB_SEARCH_TOOL],
                    messages=messages,
                ) as stream:
                    response = await stream.get_final_message()

                if response.stop_reason == "pause_turn":
                    if retries >= MAX_PAUSE_TURN_RETRIES:
                        logger.warning(
                            "enrich firm '%s': pause_turn loop exhausted",
                            firm_name,
                        )
                        break
                    retries += 1
                    messages = [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": response.content},
                    ]
                    continue
                break

            text_parts = [
                b.text for b in response.content if b.type == "text"
            ]
            full_text = "\n\n".join(text_parts)
            parsed = _extract_json(full_text)
            if parsed is None:
                logger.warning(
                    "enrich firm '%s': JSON parse failed, raw=%r",
                    firm_name, full_text[:300],
                )
                return {"_enrichment_error": "Model output unparseable as JSON"}

            return _normalize_enrichment(parsed)

        except Exception as exc:
            logger.exception(
                "enrich firm '%s' failed: %s", firm_name, exc,
            )
            return {
                "_enrichment_error": f"{type(exc).__name__}: {exc}"[:400]
            }


def _normalize_enrichment(parsed: dict) -> dict[str, Any]:
    """Translate model JSON to our underscore-prefixed firms_data keys.

    Also computes the firm-vs-individual band gap so the UI doesn't have
    to. Bands are integers 1-5+ in Chambers (1 best); a gap of 2+ tiers
    is the warning threshold.
    """
    def as_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [as_text(item) for item in value]
            joined = "; ".join(part for part in parts if part)
            return joined or None
        return None

    def as_int(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            m = re.search(r"\d+", value)
            return int(m.group(0)) if m else None
        return None

    def as_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "y", "1"}:
                return True
            if normalized in {"false", "no", "n", "0"}:
                return False
        return None

    def as_text_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [text for item in value if (text := as_text(item))]
        text = as_text(value)
        return [text] if text else []

    def as_alternates(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        out: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = as_text(item.get("name"))
            if not name:
                continue
            out.append({
                "name": name,
                "band": as_int(item.get("band")),
                "fit_for_case": as_text(item.get("fit_for_case")),
                "takes_outside_consults": as_bool(item.get("takes_outside_consults")),
            })
        return out

    out: dict[str, Any] = {
        "_lead_attorney_band": as_int(parsed.get("lead_attorney_band")),
        "_lead_attorney_band_source": as_text(parsed.get("lead_attorney_band_source")),
        "_lead_attorney_band_year": as_int(parsed.get("lead_attorney_band_year")),
        "_lead_attorney_practice_focus": as_text(parsed.get("lead_attorney_practice_focus")),
        "_lead_attorney_credentials": as_text_list(parsed.get("lead_attorney_credentials")),
        "_lead_attorney_takes_outside_consults": as_bool(
            parsed.get("lead_attorney_takes_outside_consults")
        ),
        "_individual_vs_firm_band_gap_warning": as_text(
            parsed.get("individual_vs_firm_band_gap_warning")
        ),
        "_alternate_attorneys": as_alternates(parsed.get("alternate_attorneys")),
        "_verified_sources": as_text_list(parsed.get("verified_sources")),
        "_rfe_pattern": as_text(parsed.get("rfe_pattern")),
        "_enriched_at": _dt.datetime.utcnow().isoformat(),
    }
    return out


# ---------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------

def _firm_band_from_credentials(creds: list[str]) -> int | None:
    """Pull a firm-level Chambers/Legal500 band out of free-text credentials.

    The personas output 'Chambers USA Band 1' style strings; we want the
    integer to compute the gap. Best-effort regex; returns None when no
    band is parseable.
    """
    band_re = re.compile(r"\bBand\s*([1-5])\b", re.IGNORECASE)
    for c in creds or []:
        m = band_re.search(str(c))
        if m:
            return int(m.group(1))
    return None


def _compute_band_gap(firm: dict[str, Any], enriched: dict[str, Any]) -> int | None:
    """Compute firm_band - lead_attorney_band when both are known.

    Positive value = lead attorney is below firm. None when either is
    unknown.
    """
    firm_creds = firm.get("_credentials") or firm.get("credentials") or []
    firm_band = _firm_band_from_credentials(firm_creds)
    attorney_band = enriched.get("_lead_attorney_band")
    if firm_band is None or attorney_band is None:
        return None
    try:
        return int(attorney_band) - int(firm_band)
    except (TypeError, ValueError):
        return None


async def _enrich_all_firms(
    firms: list[dict[str, Any]],
    *,
    purpose: str,
    case_brief: str,
) -> list[dict[str, Any]]:
    """Run per-firm enrichment in parallel with bounded concurrency."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set; cannot enrich firms")

    http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0))
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        http_client=http_client,
        max_retries=1,
    )
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _wrap(firm: dict[str, Any]) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(
                _enrich_one_firm(
                    client, firm,
                    purpose=purpose,
                    case_brief=case_brief,
                    sem=sem,
                ),
                timeout=PER_FIRM_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            return {
                "_enrichment_error": (
                    f"Enrichment timed out after {PER_FIRM_TIMEOUT_S}s"
                )
            }

    try:
        results = await asyncio.gather(*[_wrap(f) for f in firms])
    finally:
        await http_client.aclose()

    # Merge each enrichment dict into its firm dict (preserving existing
    # keys; underscore-prefixed enrichment keys overwrite cleanly).
    merged: list[dict[str, Any]] = []
    for firm, enriched in zip(firms, results):
        if "_enrichment_error" in enriched:
            merged.append({**firm, **enriched})
            continue
        # Compute the gap before merging so callers can sort by it.
        gap = _compute_band_gap(firm, enriched)
        merged.append({**firm, **enriched, "_individual_band_gap": gap})
    return merged


# ---------------------------------------------------------------------
# Public entrypoint — called from FastAPI BackgroundTasks
# ---------------------------------------------------------------------

def run_enrichment_sync(request_id: str) -> None:
    """Stage 2 entrypoint. Invoked from `POST /{id}/checkout` as a
    background task, runs in parallel with the user's Stripe session.

    Idempotent: re-running on a row with `enrichment_status=complete`
    overwrites the underscore-prefixed enrichment keys with fresh data.
    Used by the reaper to recover from SIGTERM mid-flight.
    """
    engine = get_engine()
    with Session(engine) as db:
        row = db.get(ProfessionalSearchRequestRow, request_id)
        if row is None:
            logger.error("enrichment: search %s not found", request_id)
            return
        if not row.firms_data:
            logger.warning(
                "enrichment: search %s has no firms_data — skipping",
                request_id,
            )
            row.enrichment_status = "failed"
            row.enrichment_error = "No firms_data on row; nothing to enrich."
            row.enrichment_completed_at = _dt.datetime.utcnow()
            db.commit()
            return

        # Mark enriching with a fresh start timestamp. If the row was
        # already enriching (re-dispatch from reaper), start over from now
        # so the grace window resets.
        row.enrichment_status = "enriching"
        row.enrichment_started_at = _dt.datetime.utcnow()
        row.enrichment_error = None
        db.commit()

        firms_in: list[dict[str, Any]] = list(row.firms_data)
        purpose = row.purpose
        case_brief = row.case_brief or ""

        try:
            firms_out = asyncio.run(
                _enrich_all_firms(
                    firms_in, purpose=purpose, case_brief=case_brief,
                )
            )
            row.firms_data = firms_out
            row.enrichment_status = "complete"
            row.enrichment_completed_at = _dt.datetime.utcnow()
            row.enrichment_error = None
            db.commit()
            errored = sum(1 for f in firms_out if "_enrichment_error" in f)
            logger.info(
                "enrichment: %s complete (%d firms, %d errored)",
                request_id, len(firms_out), errored,
            )
        except Exception as exc:
            logger.exception("enrichment: %s failed", request_id)
            row.enrichment_status = "failed"
            row.enrichment_error = f"{type(exc).__name__}: {exc}"[:500]
            row.enrichment_completed_at = _dt.datetime.utcnow()
            db.commit()
