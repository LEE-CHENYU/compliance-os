"""Generate document checklist slots from discovery answers."""

import re
from compliance_os.web.models.schemas import DocumentSlot


def _get_answer(answers: list[dict], key: str):
    """Extract answer value for a given question key."""
    for a in answers:
        if a.get("question_key") == key:
            return a.get("answer")
    return None


def _slugify(name: str) -> str:
    """Convert entity name to a URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def generate_checklist(answers: list[dict]) -> list[DocumentSlot]:
    """Map discovery answers to required document slots."""
    slots: list[DocumentSlot] = []
    concerns = _get_answer(answers, "concern_area") or []
    residency = _get_answer(answers, "residency_status")
    prior_filings = _get_answer(answers, "prior_filings") or []
    entities = _get_answer(answers, "entities") or []

    # Tax slots
    if "Tax Filing" in concerns:
        slots.append(DocumentSlot(key="w2_latest", label="Most recent W-2", required=True, group="Tax"))
        slots.append(DocumentSlot(key="1099s", label="Any 1099 forms received", required=False, group="Tax"))
        if "1040" in prior_filings or "1040-NR" in prior_filings:
            slots.append(DocumentSlot(key="prior_return_2024", label="Most recent tax return (1040 or 1040-NR)", required=True, group="Tax"))
            slots.append(DocumentSlot(key="prior_return_2023", label="Previous year tax return, if available", required=False, group="Tax"))

    # Immigration slots
    if "Immigration" in concerns:
        slots.append(DocumentSlot(key="i20", label="Current I-20 or approval notice", required=True, group="Immigration"))
        slots.append(DocumentSlot(key="passport_id_page", label="Passport identity page", required=True, group="Immigration"))
        slots.append(DocumentSlot(key="visa_stamp", label="Most recent visa stamp", required=False, group="Immigration"))

    # Residency-specific
    if residency in ("F-1", "H-1B", "L-1", "O-1"):
        slots.append(DocumentSlot(key="i94", label="I-94 arrival/departure record", required=True, group="Immigration"))

    # Entity slots
    if isinstance(entities, list):
        for entity in entities:
            name = entity.get("name", "entity")
            slug = _slugify(name)
            slots.append(DocumentSlot(key=f"{slug}_formation", label=f"{name} — formation documents", required=True, group="Entity"))
            slots.append(DocumentSlot(key=f"{slug}_ein_letter", label=f"{name} — EIN confirmation letter", required=True, group="Entity"))

    # Always include catch-all
    slots.append(DocumentSlot(key="other", label="Any other relevant documents", required=False, group="General", repeatable=True))

    return slots
