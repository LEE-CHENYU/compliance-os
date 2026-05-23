"""Canonical fact vocabulary for the user-facts SoT.

Guardian users share a partly-identical compliance profile across three
tracks (young_professional / student / entrepreneur). Most facts
(employer, address, immigration status, tax filing year) are shared;
each track has its own specialty fields (STEM OPT DSO, NAICS code,
CPT term…).

This file defines the controlled-vocabulary side of the schema. Each
canonical key maps to a FactDef with the human label, category, and
the tracks it applies to. Ad-hoc keys are still allowed (with a
"custom:" prefix on the `fact_key` column); they just don't show up in
the per-track templates.

When adding a key: keep the snake_case identifier specific enough that
the field name is unambiguous ("h1b_classification_end_date", not
just "end_date"). The label is what shows in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass


CATEGORIES = ("immigration", "tax", "corporate", "personal", "employment", "education")
TRACKS = ("shared", "young_professional", "student", "entrepreneur")


@dataclass(frozen=True)
class FactDef:
    """Canonical definition for a single fact_key."""

    label: str
    category: str
    track: str
    # Optional: extractor hint — the doc_type(s) this fact is typically
    # found in. Used by the post-upload supersession hook to scope
    # which uploads might supersede this fact's source document.
    typical_doc_types: tuple[str, ...] = ()
    # Optional: how the value is shaped at the JSON level. Mostly for
    # UI rendering; the column accepts any JSON regardless.
    shape: str = "string"  # string | number | date | object | list

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"unknown category: {self.category}")
        if self.track not in TRACKS:
            raise ValueError(f"unknown track: {self.track}")


CANONICAL_FACTS: dict[str, FactDef] = {
    # ─── Shared identity / personal ─────────────────────────────
    "legal_name": FactDef(
        "Legal name (as on passport / SSN card)",
        "personal", "shared",
        typical_doc_types=("passport", "ssn_card", "i797", "i20"),
    ),
    "date_of_birth": FactDef(
        "Date of birth",
        "personal", "shared",
        typical_doc_types=("passport", "i797", "i20"),
        shape="date",
    ),
    "country_of_birth": FactDef(
        "Country of birth",
        "personal", "shared",
        typical_doc_types=("passport", "i797", "i20"),
    ),
    "country_of_citizenship": FactDef(
        "Country of citizenship",
        "personal", "shared",
        typical_doc_types=("passport", "i797", "i20"),
    ),
    "ssn_last4": FactDef(
        "SSN (last 4)",
        "personal", "shared",
        typical_doc_types=("ssn_card", "w2", "1040_nr"),
    ),
    "current_residential_address": FactDef(
        "Current residential address",
        "personal", "shared",
        typical_doc_types=("lease", "w2", "1040_nr", "uscis_correspondence"),
        shape="object",  # {street, unit, city, state, zip, country}
    ),
    "passport_number": FactDef(
        "Passport number",
        "personal", "shared",
        typical_doc_types=("passport",),
    ),
    "passport_expiry": FactDef(
        "Passport expiry date",
        "personal", "shared",
        typical_doc_types=("passport",),
        shape="date",
    ),

    # ─── Shared immigration ─────────────────────────────────────
    "current_immigration_status": FactDef(
        "Current immigration status (F-1 / OPT / STEM OPT / H-1B / …)",
        "immigration", "shared",
        typical_doc_types=("i797", "i20", "ead"),
    ),
    "current_status_end_date": FactDef(
        "Current status valid-until date",
        "immigration", "shared",
        typical_doc_types=("i797", "i20", "ead"),
        shape="date",
    ),
    "i94_admission_number": FactDef(
        "Most recent I-94 admission number",
        "immigration", "shared",
        typical_doc_types=("i94",),
    ),
    "i94_class_of_admission": FactDef(
        "I-94 class of admission",
        "immigration", "shared",
        typical_doc_types=("i94",),
    ),
    "i94_admit_until_date": FactDef(
        "I-94 admit-until date",
        "immigration", "shared",
        typical_doc_types=("i94",),
        shape="date",
    ),

    # ─── Shared employment ──────────────────────────────────────
    "current_employer_legal_name": FactDef(
        "Current employer (legal name)",
        "employment", "shared",
        typical_doc_types=("offer_letter", "employment_letter", "i797", "w2", "paystub"),
    ),
    "current_employer_ein": FactDef(
        "Current employer EIN",
        "employment", "shared",
        typical_doc_types=("w2", "ein_letter"),
    ),
    "current_position_title": FactDef(
        "Current position title",
        "employment", "shared",
        typical_doc_types=("offer_letter", "employment_letter", "i797"),
    ),
    "current_annual_salary": FactDef(
        "Current annual salary",
        "employment", "shared",
        typical_doc_types=("offer_letter", "w2", "paystub"),
        shape="number",
    ),
    "employment_start_date": FactDef(
        "Current employment start date",
        "employment", "shared",
        typical_doc_types=("offer_letter", "i9"),
        shape="date",
    ),
    "worksite_address": FactDef(
        "Worksite address",
        "employment", "shared",
        typical_doc_types=("offer_letter", "i983", "lca"),
        shape="object",
    ),

    # ─── Shared tax ─────────────────────────────────────────────
    "tax_residency_classification": FactDef(
        "Tax residency classification (resident / nonresident / dual-status)",
        "tax", "shared",
        typical_doc_types=("8843", "1040_nr", "1040"),
    ),
    "form_8843_filed_year": FactDef(
        "Most recent Form 8843 filing year",
        "tax", "shared",
        typical_doc_types=("8843",),
        shape="number",
    ),
    "form_1040nr_filed_year": FactDef(
        "Most recent 1040-NR filing year",
        "tax", "shared",
        typical_doc_types=("1040_nr",),
        shape="number",
    ),
    "fbar_filed_year": FactDef(
        "Most recent FBAR (FinCEN 114) filing year",
        "tax", "shared",
        typical_doc_types=("fbar",),
        shape="number",
    ),
    "foreign_account_aggregate_high": FactDef(
        "Aggregate high balance across foreign accounts (USD)",
        "tax", "shared",
        typical_doc_types=("fbar",),
        shape="number",
    ),

    # ─── Young Professional / H-1B chain ────────────────────────
    "h1b_receipt_number": FactDef(
        "H-1B receipt number (I-797)",
        "immigration", "young_professional",
        typical_doc_types=("i797",),
    ),
    "h1b_classification_start_date": FactDef(
        "H-1B classification start date",
        "immigration", "young_professional",
        typical_doc_types=("i797",),
        shape="date",
    ),
    "h1b_classification_end_date": FactDef(
        "H-1B classification end date",
        "immigration", "young_professional",
        typical_doc_types=("i797",),
        shape="date",
    ),
    "h1b_amendment_dates": FactDef(
        "H-1B amendments (receipt numbers + dates)",
        "immigration", "young_professional",
        typical_doc_types=("i797",),
        shape="list",
    ),
    "lca_case_number": FactDef(
        "LCA case number (ETA-9035)",
        "immigration", "young_professional",
        typical_doc_types=("lca",),
    ),
    "stem_opt_start_date": FactDef(
        "STEM OPT start date",
        "immigration", "young_professional",
        typical_doc_types=("ead", "i20"),
        shape="date",
    ),
    "stem_opt_end_date": FactDef(
        "STEM OPT end date",
        "immigration", "young_professional",
        typical_doc_types=("ead", "i20"),
        shape="date",
    ),
    "i983_employer_evp_signature_date": FactDef(
        "I-983 employer EVP signature date",
        "immigration", "young_professional",
        typical_doc_types=("i983",),
        shape="date",
    ),
    "i983_dso_signature_date": FactDef(
        "I-983 DSO signature date",
        "immigration", "young_professional",
        typical_doc_types=("i983",),
        shape="date",
    ),

    # ─── International Student / F-1 ────────────────────────────
    "sevis_id": FactDef(
        "SEVIS ID",
        "immigration", "student",
        typical_doc_types=("i20",),
    ),
    "i20_program_start_date": FactDef(
        "I-20 program start date",
        "immigration", "student",
        typical_doc_types=("i20",),
        shape="date",
    ),
    "i20_program_end_date": FactDef(
        "I-20 program end date",
        "immigration", "student",
        typical_doc_types=("i20",),
        shape="date",
    ),
    "i20_school_name": FactDef(
        "School (per I-20)",
        "immigration", "student",
        typical_doc_types=("i20",),
    ),
    "dso_name": FactDef(
        "Designated School Official (DSO) name",
        "immigration", "student",
        typical_doc_types=("i20",),
    ),
    "dso_email": FactDef(
        "DSO email",
        "immigration", "student",
        typical_doc_types=("i20",),
    ),
    "cpt_term_start_date": FactDef(
        "CPT term start date",
        "immigration", "student",
        typical_doc_types=("i20",),
        shape="date",
    ),
    "cpt_term_end_date": FactDef(
        "CPT term end date",
        "immigration", "student",
        typical_doc_types=("i20",),
        shape="date",
    ),

    # ─── Entrepreneur / foreign-owned entity ────────────────────
    "entity_legal_name": FactDef(
        "Entity legal name",
        "corporate", "entrepreneur",
        typical_doc_types=("articles", "ein_letter", "1120", "5472"),
    ),
    "entity_ein": FactDef(
        "Entity EIN",
        "corporate", "entrepreneur",
        typical_doc_types=("ein_letter", "1120"),
    ),
    "entity_state_of_formation": FactDef(
        "Entity state of formation",
        "corporate", "entrepreneur",
        typical_doc_types=("articles",),
    ),
    "entity_formation_date": FactDef(
        "Entity formation date",
        "corporate", "entrepreneur",
        typical_doc_types=("articles",),
        shape="date",
    ),
    "entity_naics_code": FactDef(
        "Entity NAICS code",
        "corporate", "entrepreneur",
        typical_doc_types=("articles", "ss4"),
    ),
    "entity_registered_agent": FactDef(
        "Entity registered agent",
        "corporate", "entrepreneur",
        typical_doc_types=("articles",),
    ),
    "entity_hq_address": FactDef(
        "Entity HQ address",
        "corporate", "entrepreneur",
        typical_doc_types=("articles", "lease"),
        shape="object",
    ),
    "shareholders": FactDef(
        "Shareholders (name + %)",
        "corporate", "entrepreneur",
        typical_doc_types=("stock_cert", "board_resolution", "5472"),
        shape="list",
    ),
    "form_5472_filed_year": FactDef(
        "Most recent Form 5472 filing year",
        "tax", "entrepreneur",
        typical_doc_types=("5472",),
        shape="number",
    ),

    # ─── Education credentials (shared, common across visa filings) ──
    "highest_degree_school": FactDef(
        "Highest degree — institution",
        "education", "shared",
        typical_doc_types=("diploma", "transcript"),
    ),
    "highest_degree_field": FactDef(
        "Highest degree — field of study",
        "education", "shared",
        typical_doc_types=("diploma", "transcript"),
    ),
    "highest_degree_award_date": FactDef(
        "Highest degree — award date",
        "education", "shared",
        typical_doc_types=("diploma", "transcript"),
        shape="date",
    ),

    # ─── Counsel / professional engagement (shared) ─────────────
    "immigration_counsel_name": FactDef(
        "Immigration counsel (attorney / firm)",
        "personal", "shared",
        typical_doc_types=("engagement_letter",),
    ),
    "tax_preparer_name": FactDef(
        "Tax preparer (CPA / firm)",
        "personal", "shared",
        typical_doc_types=("engagement_letter",),
    ),
}


def is_canonical_key(fact_key: str) -> bool:
    """True if fact_key is in the controlled vocabulary."""
    return fact_key in CANONICAL_FACTS


def resolve_fact_def(fact_key: str) -> FactDef | None:
    """Return the FactDef for a canonical key, or None for ad-hoc keys."""
    return CANONICAL_FACTS.get(fact_key)


def canonical_keys_for_track(track: str) -> list[str]:
    """Return canonical fact_keys that apply to a track.

    Shared keys are included in every track's list; track-specific keys
    are added on top. Use this for the per-track "12 of 18 facts
    captured" progress UI.
    """
    if track not in TRACKS:
        raise ValueError(f"unknown track: {track}")
    return [
        key for key, fd in CANONICAL_FACTS.items()
        if fd.track == "shared" or fd.track == track
    ]
