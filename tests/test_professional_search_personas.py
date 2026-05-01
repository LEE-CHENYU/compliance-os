from __future__ import annotations

import datetime as dt
from pathlib import Path

from compliance_os.professional_search.ingest import VERTICAL_DEFAULTS
from compliance_os.professional_search.personas import (
    build_search_plan,
    list_personas,
    select_personas,
)
from compliance_os.web.models.tables import ProfessionalSearchRequestRow
from compliance_os.web.routers.professional_search import (
    _normalize_tier_report,
    _render_html,
    _render_markdown,
    _serialize,
)
from compliance_os.web.services.enrichment_runner import _normalize_enrichment


def test_every_configured_professional_search_vertical_has_personas() -> None:
    for vertical in sorted(VERTICAL_DEFAULTS):
        personas = list_personas(vertical)

        assert len(personas) >= 3, vertical
        assert len({p.id for p in personas}) == len(personas)
        assert all(p.vertical == vertical for p in personas)

        for persona in personas:
            assert persona.raw.get("search_angle"), persona.id
            assert persona.raw.get("must_weight"), persona.id
            assert persona.raw.get("target_count"), persona.id


def test_public_attorney_and_cpa_personas_are_case_selective() -> None:
    public_verticals = {
        "immigration_attorney",
        "immigration_eb5",
        "tax_attorney",
        "corporate_attorney",
        "cpa",
    }

    for vertical in public_verticals:
        missing = [p.id for p in list_personas(vertical) if not p.raw.get("activation")]
        assert missing == [], f"{vertical} personas missing activation: {missing}"


def test_bundled_personas_win_over_local_data_mirror() -> None:
    personas = {p.id: p for p in list_personas("immigration_attorney")}

    assert "personas_data" in personas["elite_boutique"].path.parts


def test_cpa_search_plan_builds_dispatch_prompts(tmp_path: Path) -> None:
    plan = build_search_plan(
        case_brief=(
            "Need a CPA for nonresident tax filing, Form 1040-NR, Form 8843, "
            "FBAR screening, and a foreign-owned US disregarded LLC with prior "
            "year cleanup and bookkeeping questions."
        ),
        purpose="CPA tax engagement",
        vertical="cpa",
        output_dir=tmp_path,
    )

    persona_ids = {prompt["persona_id"] for prompt in plan["prompts"]}
    assert persona_ids == {
        "foreign_owned_entity",
        "founder_accounting",
        "international_tax",
    }
    assert plan["selected_personas"] == [
        "international_tax",
        "foreign_owned_entity",
        "founder_accounting",
    ]
    assert {item["id"] for item in plan["skipped_personas"]} == {
        "audit_defense",
        "equity_crypto_tax",
        "expat_tax",
        "state_sales_tax",
    }
    assert plan["vertical"] == "cpa"
    assert all(Path(path).parent == tmp_path for path in plan["output_paths"])
    assert "lead_contact" in plan["prompts"][0]["prompt"]


def test_cpa_persona_selection_prunes_irrelevant_founder_accounting() -> None:
    selection = select_personas(
        "cpa",
        purpose="Nonresident tax filing",
        case_brief=(
            "I need a CPA for Form 1040-NR, Form 8843, FBAR screening, FATCA "
            "questions, and a foreign-owned LLC Form 5472 filing. No IRS notice "
            "and no bookkeeping or payroll support is needed."
        ),
    )

    assert [p.id for p in selection.selected] == [
        "international_tax",
        "foreign_owned_entity",
    ]
    assert {item["id"] for item in selection.skipped} == {
        "audit_defense",
        "equity_crypto_tax",
        "expat_tax",
        "founder_accounting",
        "state_sales_tax",
    }


def test_cpa_persona_selection_runs_accounting_when_books_are_in_scope() -> None:
    selection = select_personas(
        "cpa",
        purpose="Startup books and tax cleanup",
        case_brief=(
            "The founder needs QuickBooks cleanup, Stripe transaction review, "
            "payroll setup, contractor 1099 support, and quarterly estimates "
            "for an early-stage LLC."
        ),
    )

    assert "founder_accounting" in {p.id for p in selection.selected}


def test_immigration_persona_selection_targets_status_issue_without_broad_run() -> None:
    selection = select_personas(
        "immigration_attorney",
        purpose="F-1 OPT status risk consult",
        case_brief=(
            "Need an immigration attorney for an F-1 student who used CPT, "
            "has STEM OPT unemployment-day and SEVIS questions, and may need "
            "reinstatement or travel advice before an H-1B change of status."
        ),
    )

    selected_ids = {p.id for p in selection.selected}
    assert "student_opt_status" in selected_ids
    assert "family_humanitarian" not in selected_ids
    assert "employment_green_card" not in selected_ids


def test_enrichment_normalization_protects_client_from_model_shape_drift() -> None:
    normalized = _normalize_enrichment({
        "lead_attorney_band": "Band 2",
        "lead_attorney_band_source": {"source": "unexpected object"},
        "lead_attorney_band_year": "2025",
        "lead_attorney_practice_focus": ["employment immigration", "founders"],
        "lead_attorney_credentials": "Chambers profile",
        "lead_attorney_takes_outside_consults": "no",
        "individual_vs_firm_band_gap_warning": {"warning": "unexpected object"},
        "alternate_attorneys": "not a list",
        "verified_sources": [{"url": "unexpected object"}, "https://example.com"],
        "rfe_pattern": 123,
    })

    assert normalized["_lead_attorney_band"] == 2
    assert normalized["_lead_attorney_band_source"] is None
    assert normalized["_lead_attorney_band_year"] == 2025
    assert normalized["_lead_attorney_practice_focus"] == "employment immigration; founders"
    assert normalized["_lead_attorney_credentials"] == ["Chambers profile"]
    assert normalized["_lead_attorney_takes_outside_consults"] is False
    assert normalized["_individual_vs_firm_band_gap_warning"] is None
    assert normalized["_alternate_attorneys"] == []
    assert normalized["_verified_sources"] == ["https://example.com"]
    assert normalized["_rfe_pattern"] == "123"


def test_tier_report_normalization_adds_firm_alias_for_vendor_rows() -> None:
    rows = _normalize_tier_report([
        {"vendor": "Bright!Tax", "vendor_type": "cpa", "score": 74},
        {"firm": "Immigration LLP", "score": 91},
        {"name": "Fallback Vendor", "score": 50},
    ])

    assert rows == [
        {"vendor": "Bright!Tax", "vendor_type": "cpa", "score": 74, "firm": "Bright!Tax"},
        {"firm": "Immigration LLP", "score": 91},
        {"name": "Fallback Vendor", "score": 50, "firm": "Fallback Vendor"},
    ]


def test_pdf_html_report_includes_stage_two_enrichment() -> None:
    row = ProfessionalSearchRequestRow(
        id="stage2-test",
        case_brief="Need H-1B owner-beneficiary counsel for a founder case.",
        purpose="H-1B owner-beneficiary lawyer search",
        vertical="immigration_attorney",
        status="complete",
        persona_status={},
        tier_report=[],
        firms_data=[
            {
                "name": "Foster LLP",
                "confidence": 91,
                "lead_contact": "Robert Loughran",
                "role": "Partner",
                "city": "Houston",
                "state": "TX",
                "_personas": ["elite_boutique"],
                "_why_fits": [
                    ("elite_boutique", "Strong business immigration bench."),
                ],
                "_credentials": ["Chambers USA Firm Band 1"],
                "_lead_attorney_band": 2,
                "_lead_attorney_band_source": "Chambers USA",
                "_lead_attorney_band_year": 2025,
                "_lead_attorney_practice_focus": "Business immigration and H-1B matters",
                "_lead_attorney_credentials": [
                    "Chambers USA Band 2 - Texas Immigration (2025)",
                ],
                "_lead_attorney_takes_outside_consults": False,
                "_individual_vs_firm_band_gap_warning": (
                    "Firm Band 1, lead attorney Band 2 - verify routing."
                ),
                "_alternate_attorneys": [
                    {
                        "name": "Helene Dang",
                        "band": 1,
                        "band_source": "Chambers USA",
                        "fit_for_case": "Direct H-1B founder case match.",
                        "takes_outside_consults": True,
                    }
                ],
                "_verified_sources": ["https://example.com/chambers-robert-loughran"],
                "_enrichment_error": "RuntimeError: provider timeout with internal trace",
            }
        ],
        created_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        completed_at=dt.datetime(2026, 1, 1, 12, 10, 0),
        paid_at=dt.datetime(2026, 1, 1, 12, 11, 0),
    )

    html = _render_html(row)

    assert "Stage 2 individual verification" in html
    assert "Robert Loughran" in html
    assert "Chambers USA Band 2 (2025)" in html
    assert "May not take outside consults" in html
    assert "Firm Band 1, lead attorney Band 2 - verify routing." in html
    assert "Business immigration and H-1B matters" in html
    assert "Helene Dang" in html
    assert "Individual verification sources" in html
    assert "https://example.com/chambers-robert-loughran" in html
    assert "RuntimeError" not in html
    assert "provider timeout" not in html


def test_cpa_report_uses_professional_provider_copy_not_attorney_copy(
    tmp_path: Path,
) -> None:
    persona_path = tmp_path / "international_tax.yaml"
    persona_path.write_text(
        """
firms:
  - name: BrightTax Advisors
    confidence: 82
    city: New York
    state: NY
    why_fit: Strong nonresident and cross-border tax focus.
    credentials:
      - IRS enrolled agent and CPA references
""".strip()
    )

    row = ProfessionalSearchRequestRow(
        id="cpa-copy-test",
        case_brief=(
            "Need a CPA for nonresident 1040-NR, Form 8843, FBAR screening, "
            "and foreign-owned disregarded LLC Form 5472 cleanup."
        ),
        purpose="CPA tax engagement",
        vertical="cpa",
        status="complete",
        persona_status={
            "international_tax": {
                "status": "complete",
                "output_path": str(persona_path),
            }
        },
        tier_report=[],
        firms_data=[
            {
                "name": "BrightTax Advisors",
                "confidence": 82,
                "city": "New York",
                "state": "NY",
                "_personas": ["international_tax"],
                "_why_fits": [
                    ("international_tax", "Strong nonresident and cross-border tax focus."),
                ],
                "_credentials": ["IRS enrolled agent and CPA references"],
                "_lead_attorney_credentials": ["CPA license active in NY"],
                "_lead_attorney_practice_focus": "Nonresident tax and foreign-owned LLC compliance",
                "_alternate_attorneys": [
                    {
                        "name": "Dana Chen",
                        "fit_for_case": "Handles Form 5472 cleanup and FBAR screening.",
                    }
                ],
                "_verified_sources": ["https://example.com/cpa-license"],
            }
        ],
        created_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        completed_at=dt.datetime(2026, 1, 1, 12, 10, 0),
        paid_at=dt.datetime(2026, 1, 1, 12, 11, 0),
    )

    html = _render_html(row)
    markdown = _render_markdown(row)

    assert "CPA practices" in html
    assert "CPA practice dossiers" in html
    assert "Lead CPA/contact" in html
    assert "Same-practice alternates" in html
    assert "Lawyer search" not in html
    assert "Top firms" not in html
    assert "Firm dossiers" not in html
    assert "Lead attorney" not in html
    assert "Better-fit attorneys" not in html
    assert "Same-firm alternates" not in html
    assert "# Professional search — CPA tax engagement" in markdown
    assert "**Why this CPA practice**" in markdown


def test_public_search_payload_redacts_worker_internal_details() -> None:
    row = ProfessionalSearchRequestRow(
        id="public-payload-test",
        case_brief="Need H-1B owner-beneficiary counsel for a founder case.",
        purpose="H-1B owner-beneficiary lawyer search",
        vertical="immigration_attorney",
        status="failed",
        error="RuntimeError: raw internal runner exception",
        persona_status={
            "elite_boutique": {
                "status": "failed",
                "output_path": "/tmp/private/persona.yaml",
                "error": "Traceback: private worker exception",
                "input_tokens": 1234,
                "output_tokens": 567,
                "cache_read_tokens": 89,
                "started_at": "2026-01-01T12:00:00",
                "finished_at": "2026-01-01T12:01:00",
            },
            "audit_defense": {
                "status": "skipped",
                "reason": "internal activation score below threshold",
                "score": 0,
                "threshold": 4,
                "matched_signals": ["private signal"],
            },
        },
        tier_report=[],
        firms_data=[
            {
                "name": "Foster LLP",
                "_enriched_at": "2026-01-01T12:02:00",
                "_enrichment_error": "TimeoutError: provider request id abc123",
                "_lead_attorney_band": 2,
            }
        ],
        created_at=dt.datetime(2026, 1, 1, 12, 0, 0),
        completed_at=dt.datetime(2026, 1, 1, 12, 10, 0),
        paid_at=dt.datetime(2026, 1, 1, 12, 11, 0),
        enrichment_status="failed",
        enrichment_error="TimeoutError: provider request id abc123",
    )

    payload = _serialize(row).model_dump()

    assert "enrichment_error" not in payload
    assert payload["error"] == (
        "This search did not complete. Please retry or contact Guardian support "
        "from your dashboard."
    )
    assert payload["persona_status"]["elite_boutique"] == {
        "status": "failed",
        "started_at": "2026-01-01T12:00:00",
        "finished_at": "2026-01-01T12:01:00",
    }
    assert payload["persona_status"]["audit_defense"] == {
        "status": "skipped",
        "reason": "Skipped because this search axis was not relevant to the case.",
    }
    assert payload["firms_data"] == [
        {
            "name": "Foster LLP",
            "_enriched_at": "2026-01-01T12:02:00",
            "_lead_attorney_band": 2,
        }
    ]
    assert "provider request id" not in str(payload)
    assert "/tmp/private" not in str(payload)
