"""Map extraction (doc_type, field_name) → canonical fact_key.

The extractor writes raw fields into ExtractedFieldRow with names that
match each doc_type's schema (employer_name, sevis_number, …). Those
names don't always line up with the SoT vocabulary's keys
(current_employer_legal_name, sevis_id, …). This module is the bridge.

When `_upsert_extracted_field` lands a new field, it calls
`fact_key_for(doc_type, field_name)`. If a canonical key comes back,
the document_store also upserts a user_facts row sourced from this
document. Unmapped fields stay in ExtractedFieldRow only — the SoT
table is opinionated about which fields are worth tracking centrally.
"""

from __future__ import annotations


# Keys: (doc_type, field_name) → canonical fact_key in vocabulary.py.
# Add a row here when a new extractor field should flow into the SoT.
EXTRACTION_TO_FACT_KEY: dict[tuple[str, str], str] = {
    # ─── I-797 (H-1B approval / amendment) ─────────────────
    ("i797", "receipt_number"):            "h1b_receipt_number",
    ("i797", "valid_from"):                "h1b_classification_start_date",
    ("i797", "valid_to"):                  "h1b_classification_end_date",
    ("i797", "beneficiary_name"):          "legal_name",
    ("i797", "petitioner_name"):           "current_employer_legal_name",
    ("i797", "classification"):            "current_immigration_status",

    # ─── I-20 (F-1 / STEM OPT) ─────────────────────────────
    ("i20",  "student_name"):              "legal_name",
    ("i20",  "sevis_number"):              "sevis_id",
    ("i20",  "school_name"):               "i20_school_name",
    ("i20",  "program_start_date"):        "i20_program_start_date",
    ("i20",  "program_end_date"):          "i20_program_end_date",
    ("i20",  "dso_name"):                  "dso_name",
    ("i20",  "dso_email"):                 "dso_email",
    ("i20",  "cpt_start_date"):            "cpt_term_start_date",
    ("i20",  "cpt_end_date"):              "cpt_term_end_date",

    # ─── I-983 (STEM OPT training plan) ────────────────────
    ("i983", "student_name"):              "legal_name",
    ("i983", "sevis_number"):              "sevis_id",
    ("i983", "school_name"):               "i20_school_name",
    ("i983", "employer_name"):             "current_employer_legal_name",
    ("i983", "employer_ein"):              "current_employer_ein",
    ("i983", "job_title"):                 "current_position_title",
    ("i983", "compensation"):              "current_annual_salary",
    ("i983", "start_date"):                "employment_start_date",
    ("i983", "work_site_address"):         "worksite_address",

    # ─── EAD card / I-766 (STEM OPT) ───────────────────────
    ("ead",  "valid_from"):                "stem_opt_start_date",
    ("ead",  "valid_to"):                  "stem_opt_end_date",
    ("ead",  "category"):                  "current_immigration_status",
    ("ead",  "card_holder_name"):          "legal_name",

    # ─── I-94 ──────────────────────────────────────────────
    ("i94",  "admission_number"):          "i94_admission_number",
    ("i94",  "class_of_admission"):        "i94_class_of_admission",
    ("i94",  "admit_until_date"):          "i94_admit_until_date",

    # ─── Employment letter / offer letter ──────────────────
    ("employment_letter", "employee_name"):"legal_name",
    ("employment_letter", "employer_name"):"current_employer_legal_name",
    ("employment_letter", "job_title"):    "current_position_title",
    ("employment_letter", "compensation"): "current_annual_salary",
    ("employment_letter", "work_location"):"worksite_address",
    ("employment_letter", "start_date"):   "employment_start_date",
    ("offer_letter",      "employee_name"):"legal_name",
    ("offer_letter",      "employer_name"):"current_employer_legal_name",
    ("offer_letter",      "job_title"):    "current_position_title",
    ("offer_letter",      "compensation"): "current_annual_salary",
    ("offer_letter",      "work_location"):"worksite_address",
    ("offer_letter",      "start_date"):   "employment_start_date",

    # ─── W-2 ──────────────────────────────────────────────
    ("w2", "employee_name"):               "legal_name",
    ("w2", "employer_name"):               "current_employer_legal_name",
    ("w2", "employer_ein"):                "current_employer_ein",
    ("w2", "employee_address"):            "current_residential_address",
    ("w2", "ssn_last4"):                   "ssn_last4",

    # ─── Form 8843 ────────────────────────────────────────
    ("form_8843", "tax_year"):             "form_8843_filed_year",
    ("form_8843", "name"):                 "legal_name",

    # ─── Form 1040-NR ─────────────────────────────────────
    ("form_1040_nr", "tax_year"):          "form_1040nr_filed_year",
    ("form_1040_nr", "filer_name"):        "legal_name",
    ("form_1040_nr", "filing_status"):     "tax_residency_classification",

    # ─── FBAR / FinCEN 114 ────────────────────────────────
    ("fbar", "filing_year"):               "fbar_filed_year",
    ("fbar", "aggregate_high"):            "foreign_account_aggregate_high",

    # ─── Corporate / Articles of Incorporation ────────────
    ("articles", "entity_name"):           "entity_legal_name",
    ("articles", "state_of_formation"):    "entity_state_of_formation",
    ("articles", "formation_date"):        "entity_formation_date",
    ("articles", "naics_code"):            "entity_naics_code",
    ("articles", "registered_agent"):      "entity_registered_agent",
    ("articles", "hq_address"):            "entity_hq_address",

    # ─── EIN letter / CP575 ──────────────────────────────
    ("ein_letter", "entity_name"):         "entity_legal_name",
    ("ein_letter", "ein"):                 "entity_ein",

    # ─── Tax return (generic) ────────────────────────────
    ("tax_return", "entity_name"):         "entity_legal_name",
    ("tax_return", "ein"):                 "entity_ein",
    ("tax_return", "filing_status"):       "tax_residency_classification",

    # ─── Form 5472 ────────────────────────────────────────
    ("form_5472", "reporting_entity_name"):"entity_legal_name",
    ("form_5472", "tax_year"):             "form_5472_filed_year",

    # ─── Passport ────────────────────────────────────────
    ("passport", "passport_number"):       "passport_number",
    ("passport", "holder_name"):           "legal_name",
    ("passport", "date_of_birth"):         "date_of_birth",
    ("passport", "country_of_citizenship"):"country_of_citizenship",
    ("passport", "expiry_date"):           "passport_expiry",

    # ─── I-130 (petition for alien relative) ─────────────
    ("i130", "receipt_number"):            "i130_receipt_number",
    ("i130", "beneficiary_name"):          "legal_name",
    ("i130", "priority_date"):             "priority_date",
    # ─── I-485 (adjustment of status) ────────────────────
    ("i485", "receipt_number"):            "aos_receipt_number",
    ("i485", "applicant_name"):            "legal_name",
    ("i485", "priority_date"):             "priority_date",
    # ─── LCA (ETA-9035) ──────────────────────────────────
    ("lca",  "case_number"):               "lca_case_number",
    ("lca",  "soc_code"):                  "lca_soc_code",
    ("lca",  "job_title"):                 "lca_job_title",
    ("lca",  "wage_level"):                "lca_wage_level",
    ("lca",  "prevailing_wage"):           "lca_prevailing_wage",
    ("lca",  "worksite_address"):          "worksite_address",
    ("lca",  "employer_name"):             "current_employer_legal_name",
    # ─── DS-2019 (J-1 exchange visitor) ──────────────────
    ("ds2019", "student_name"):            "legal_name",
    ("ds2019", "sevis_number"):            "sevis_id",
    ("ds2019", "program_sponsor"):         "ds2019_program_sponsor",
    ("ds2019", "program_end_date"):        "ds2019_program_end_date",
    ("ds2019", "category"):                "exchange_visitor_category",
    # ─── Advance Parole (I-512) ──────────────────────────
    ("advance_parole", "valid_to"):        "advance_parole_expiry",
    ("advance_parole", "document_number"): "advance_parole_document_number",
    ("advance_parole", "holder_name"):     "legal_name",
}


def fact_key_for(doc_type: str | None, field_name: str | None) -> str | None:
    """Return the canonical fact_key for an extraction field, or None."""
    if not doc_type or not field_name:
        return None
    return EXTRACTION_TO_FACT_KEY.get((doc_type, field_name))


def schema_for_doc_type(doc_type: str) -> list[dict]:
    """Return the SoT-tracked extraction targets for a document type.

    Reverse of EXTRACTION_TO_FACT_KEY, enriched with each fact's
    human label and value shape from the vocabulary. This is exactly
    what the extraction-schema tool hands the model: which fields to
    read out of this document, and where each lands in the SoT.
    """
    from compliance_os.facts.vocabulary import resolve_fact_def

    out: list[dict] = []
    for (dt, field_name), fact_key in EXTRACTION_TO_FACT_KEY.items():
        if dt != doc_type:
            continue
        fact_def = resolve_fact_def(fact_key)
        out.append(
            {
                "source_field": field_name,
                "fact_key": fact_key,
                "label": fact_def.label if fact_def else fact_key,
                "shape": fact_def.shape if fact_def else "string",
            }
        )
    out.sort(key=lambda e: e["source_field"])
    return out
