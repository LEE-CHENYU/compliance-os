"""Generate document checklist slots from discovery answers.

Each concern area (Tax, Immigration, Corporate) generates its own
track-specific document slots. Slots are never mixed across tracks.
"""

import re
from compliance_os.web.models.schemas import DocumentSlot


def _get_answer(answers: list[dict], key: str):
    """Extract answer value for a given question key."""
    for a in answers:
        if a.get("question_key") == key:
            return a.get("answer")
    return None


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _tax_slots(answers: list[dict]) -> list[DocumentSlot]:
    """Generate document slots for the Tax track."""
    slots: list[DocumentSlot] = []
    residency = _get_answer(answers, "tax_residency_status")
    prior_filings = _get_answer(answers, "tax_prior_filings") or []
    income_sources = _get_answer(answers, "tax_income_sources") or []
    entities = _get_answer(answers, "tax_entities") or []

    # Core income documents based on sources
    if "W-2 employment" in income_sources:
        slots.append(DocumentSlot(key="tax_w2", label="W-2 (Wage and Tax Statement)", required=True, group="Tax: Income Documents"))
    if "1099 contractor" in income_sources:
        slots.append(DocumentSlot(key="tax_1099", label="1099-NEC or 1099-MISC", required=True, group="Tax: Income Documents"))
    if "Investment income" in income_sources:
        slots.append(DocumentSlot(key="tax_1099_div_int", label="1099-DIV / 1099-INT (dividends & interest)", required=False, group="Tax: Income Documents"))
    if "Foreign income" in income_sources:
        slots.append(DocumentSlot(key="tax_foreign_income_docs", label="Foreign income documentation", required=True, group="Tax: Income Documents"))
    if "Scholarship/fellowship" in income_sources:
        slots.append(DocumentSlot(key="tax_1042s", label="1042-S (Foreign Person's U.S. Source Income)", required=True, group="Tax: Income Documents"))
        slots.append(DocumentSlot(key="tax_1098t", label="1098-T (Tuition Statement)", required=False, group="Tax: Income Documents"))

    # Prior returns
    if "1040" in prior_filings or "1040-NR" in prior_filings:
        slots.append(DocumentSlot(key="tax_prior_return_recent", label="Most recent federal tax return (1040 or 1040-NR)", required=True, group="Tax: Prior Returns"))
        slots.append(DocumentSlot(key="tax_prior_return_prev", label="Previous year federal return, if available", required=False, group="Tax: Prior Returns"))
    if "State returns" in prior_filings:
        slots.append(DocumentSlot(key="tax_prior_state_return", label="Most recent state tax return", required=False, group="Tax: Prior Returns"))

    # NR-specific forms
    if residency == "Nonresident alien":
        slots.append(DocumentSlot(key="tax_8843", label="Form 8843 (Exempt Individual Statement)", required=True, group="Tax: NR-Specific"))
        slots.append(DocumentSlot(key="tax_passport", label="Passport (for SPT / entry date proof)", required=True, group="Tax: NR-Specific"))
        slots.append(DocumentSlot(key="tax_i94", label="I-94 (arrival record for entry date)", required=True, group="Tax: NR-Specific"))
        slots.append(DocumentSlot(key="tax_visa", label="Visa stamp (for status verification)", required=False, group="Tax: NR-Specific"))

    # Entity-related tax forms
    if isinstance(entities, list) and entities:
        for entity in entities:
            name = entity.get("name", "entity")
            slug = _slugify(name)
            slots.append(DocumentSlot(key=f"tax_{slug}_5472", label=f"{name} — Form 5472 (if foreign-owned)", required=False, group="Tax: Entity"))
            slots.append(DocumentSlot(key=f"tax_{slug}_return", label=f"{name} — entity tax return", required=False, group="Tax: Entity"))

    # International reporting (only for residents with foreign assets)
    if residency == "U.S. resident" or residency == "Dual-status":
        if "Foreign income" in income_sources:
            slots.append(DocumentSlot(key="tax_fbar_records", label="Foreign account records (for FBAR/FinCEN 114)", required=True, group="Tax: International"))
            slots.append(DocumentSlot(key="tax_8938_records", label="Foreign financial asset records (for Form 8938)", required=False, group="Tax: International"))

    # Catch-all
    slots.append(DocumentSlot(key="tax_other", label="Other tax documents", required=False, group="Tax: Other", repeatable=True))
    return slots


def _immigration_slots(answers: list[dict]) -> list[DocumentSlot]:
    """Generate document slots for the Immigration track."""
    slots: list[DocumentSlot] = []
    visa = _get_answer(answers, "imm_visa_category")
    subdomain = _get_answer(answers, "imm_subdomain") or []

    # Universal immigration docs (for nonimmigrants only)
    if visa in ("F-1", "H-1B", "L-1", "O-1", "J-1", "TN", "E-2", "Other visa"):
        slots.append(DocumentSlot(key="imm_passport", label="Passport identity page", required=True, group="Immigration: Identity"))
        slots.append(DocumentSlot(key="imm_visa_stamp", label="Most recent visa stamp", required=True, group="Immigration: Identity"))
        slots.append(DocumentSlot(key="imm_i94", label="I-94 (Arrival/Departure Record)", required=True, group="Immigration: Identity"))

    # F-1 specific
    if visa == "F-1":
        slots.append(DocumentSlot(key="imm_i20", label="Current I-20", required=True, group="Immigration: F-1 Status"))
        if "CPT/OPT authorization" in subdomain:
            slots.append(DocumentSlot(key="imm_ead", label="EAD card (if OPT)", required=False, group="Immigration: F-1 Status"))
            slots.append(DocumentSlot(key="imm_i983", label="I-983 Training Plan (if STEM OPT)", required=False, group="Immigration: F-1 Status"))
            slots.append(DocumentSlot(key="imm_cpt_letter", label="CPT authorization letter from DSO", required=False, group="Immigration: F-1 Status"))

    # H-1B specific
    if visa == "H-1B":
        if "Petition filing" in subdomain or "Extension/transfer" in subdomain:
            slots.append(DocumentSlot(key="imm_i129", label="I-129 (Petition for Nonimmigrant Worker)", required=True, group="Immigration: H-1B"))
            slots.append(DocumentSlot(key="imm_lca", label="LCA / ETA-9035", required=True, group="Immigration: H-1B"))
            slots.append(DocumentSlot(key="imm_approval_notice", label="I-797 Approval Notice (prior)", required=False, group="Immigration: H-1B"))
        if "Extension/transfer" in subdomain:
            slots.append(DocumentSlot(key="imm_paystubs", label="Recent paystubs (6 months)", required=True, group="Immigration: H-1B"))

    # L-1 specific
    if visa == "L-1":
        slots.append(DocumentSlot(key="imm_i129_l", label="I-129 (L-1 Petition)", required=True, group="Immigration: L-1"))
        slots.append(DocumentSlot(key="imm_blanket_l", label="Blanket L petition (if applicable)", required=False, group="Immigration: L-1"))

    # O-1 specific
    if visa == "O-1":
        slots.append(DocumentSlot(key="imm_i129_o", label="I-129 (O-1 Petition)", required=True, group="Immigration: O-1"))
        slots.append(DocumentSlot(key="imm_advisory_opinion", label="Advisory opinion / peer review", required=False, group="Immigration: O-1"))

    # Green Card holders — limited options
    if visa == "Green Card":
        slots.append(DocumentSlot(key="imm_green_card", label="Green card (front and back)", required=True, group="Immigration: Green Card"))
        slots.append(DocumentSlot(key="imm_passport_gc", label="Passport", required=True, group="Immigration: Green Card"))
        if "Naturalization" in subdomain:
            slots.append(DocumentSlot(key="imm_n400_docs", label="N-400 supporting documents (residence history, travel log)", required=True, group="Immigration: Naturalization"))
        if "Card renewal" in subdomain:
            slots.append(DocumentSlot(key="imm_i90_docs", label="I-90 supporting documents", required=True, group="Immigration: Card Renewal"))
        if "Remove conditions" in subdomain:
            slots.append(DocumentSlot(key="imm_i751_docs", label="I-751 evidence package", required=True, group="Immigration: Conditions"))

    # Citizens — very limited
    if visa == "U.S. Citizen":
        if "Records request" in subdomain:
            slots.append(DocumentSlot(key="imm_foia_docs", label="FOIA / G-639 supporting documents", required=False, group="Immigration: Records"))

    # Attorney representation
    slots.append(DocumentSlot(key="imm_g28", label="G-28 (Notice of Attorney Appearance)", required=False, group="Immigration: Representation"))

    # Catch-all
    slots.append(DocumentSlot(key="imm_other", label="Other immigration documents", required=False, group="Immigration: Other", repeatable=True))
    return slots


def _corporate_slots(answers: list[dict]) -> list[DocumentSlot]:
    """Generate document slots for the Corporate track."""
    slots: list[DocumentSlot] = []
    entities = _get_answer(answers, "corp_entities") or []
    obligations = _get_answer(answers, "corp_obligations") or []

    if isinstance(entities, list):
        for entity in entities:
            name = entity.get("name", "entity")
            slug = _slugify(name)
            slots.append(DocumentSlot(key=f"corp_{slug}_formation", label=f"{name} — formation documents (articles/operating agreement)", required=True, group=f"Corporate: {name}"))
            slots.append(DocumentSlot(key=f"corp_{slug}_ein", label=f"{name} — EIN confirmation letter", required=True, group=f"Corporate: {name}"))

            if "Annual report" in obligations:
                slots.append(DocumentSlot(key=f"corp_{slug}_annual", label=f"{name} — most recent annual report", required=False, group=f"Corporate: {name}"))
            if "Registered agent" in obligations:
                slots.append(DocumentSlot(key=f"corp_{slug}_ra", label=f"{name} — registered agent confirmation", required=False, group=f"Corporate: {name}"))
            if "Corporate minutes" in obligations:
                slots.append(DocumentSlot(key=f"corp_{slug}_minutes", label=f"{name} — corporate minutes/resolutions", required=False, group=f"Corporate: {name}"))

    # Catch-all
    slots.append(DocumentSlot(key="corp_other", label="Other corporate documents", required=False, group="Corporate: Other", repeatable=True))
    return slots


def generate_checklist(answers: list[dict]) -> list[DocumentSlot]:
    """Map discovery answers to required document slots, organized by track."""
    slots: list[DocumentSlot] = []
    concerns = _get_answer(answers, "concern_area") or []

    if "Tax Filing" in concerns:
        slots.extend(_tax_slots(answers))
    if "Immigration" in concerns:
        slots.extend(_immigration_slots(answers))
    if "Corporate Compliance" in concerns:
        slots.extend(_corporate_slots(answers))

    if not slots:
        slots.append(DocumentSlot(key="other", label="Any relevant documents", required=False, group="General", repeatable=True))

    return slots
