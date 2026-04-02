"""Generate targeted follow-up questions from discovery answers.

Questions are track-specific — tax follow-ups come from tax answers,
immigration follow-ups from immigration answers. Never cross domains.
"""


def _get_answer(answers: list[dict], key: str):
    for a in answers:
        if a.get("question_key") == key:
            return a.get("answer")
    return None


def _tax_followups(answers: list[dict]) -> list[str]:
    """Follow-up questions for the Tax track."""
    questions: list[str] = []
    residency = _get_answer(answers, "tax_residency_status")
    prior_filings = _get_answer(answers, "tax_prior_filings") or []
    stage = _get_answer(answers, "tax_filing_stage")
    entities = _get_answer(answers, "tax_entities") or []
    existing_help = _get_answer(answers, "existing_help") or []

    # NR filed as resident — common costly error
    if residency == "Nonresident alien" and "1040" in prior_filings:
        questions.append(
            "You indicated nonresident alien status but have filed Form 1040 (the resident return). "
            "This may need to be amended to 1040-NR. Was this filing prepared by a CPA, or self-prepared?"
        )

    # Amending without professional help
    if stage == "Amending prior year" and "CPA/Accountant" not in existing_help:
        questions.append(
            "Amending prior-year returns can be complex, especially if it changes your residency status. "
            "Are you working with a tax professional on the amendments?"
        )

    # Entities without CPA
    if entities and "CPA/Accountant" not in existing_help:
        questions.append(
            "Who handles the tax filings for your business entity? "
            "Entity returns (e.g., Form 5472, pro-forma 1120) have strict penalties if missed."
        )

    # NR with foreign accounts — clarify FBAR applicability
    if residency == "Nonresident alien":
        questions.append(
            "As a nonresident alien, FBAR and Form 8938 are generally not required. "
            "Have any prior preparers filed these for you? If so, that may need review."
        )

    return questions


def _immigration_followups(answers: list[dict]) -> list[str]:
    """Follow-up questions for the Immigration track."""
    questions: list[str] = []
    visa = _get_answer(answers, "imm_visa_category")
    subdomain = _get_answer(answers, "imm_subdomain") or []
    stage = _get_answer(answers, "imm_stage")
    existing_help = _get_answer(answers, "existing_help") or []

    # F-1 with CPT/OPT — common compliance gaps
    if visa == "F-1" and "CPT/OPT authorization" in subdomain:
        questions.append(
            "For CPT or OPT, your DSO must authorize employment before you start working. "
            "Has your DSO issued a new I-20 with CPT/OPT endorsement?"
        )

    # H-1B without lawyer
    if visa == "H-1B" and "Lawyer" not in existing_help:
        questions.append(
            "H-1B petitions typically require an immigration attorney (the employer files, not you). "
            "Does your employer have counsel handling the petition?"
        )

    # Green Card + naturalization timeline
    if visa == "Green Card" and "Naturalization" in subdomain:
        questions.append(
            "Naturalization eligibility depends on continuous residence and physical presence. "
            "Have you been outside the U.S. for any trips longer than 6 months?"
        )

    # Pending case without attorney
    if stage == "Pending case" and "Lawyer" not in existing_help:
        questions.append(
            "You have a pending immigration case without an attorney. "
            "Would you like help identifying immigration counsel for your situation?"
        )

    return questions


def _corporate_followups(answers: list[dict]) -> list[str]:
    """Follow-up questions for the Corporate track."""
    questions: list[str] = []
    entities = _get_answer(answers, "corp_entities") or []
    obligations = _get_answer(answers, "corp_obligations") or []
    existing_help = _get_answer(answers, "existing_help") or []

    if entities and "Annual report" in obligations and "Lawyer" not in existing_help:
        questions.append(
            "Annual report deadlines vary by state and entity type. "
            "Do you know your entity's filing deadline and registered agent status?"
        )

    return questions


def generate_followups(answers: list[dict]) -> list[str]:
    """Produce follow-up questions based on wizard answers. Track-separated."""
    questions: list[str] = []
    if not answers:
        return questions

    concerns = _get_answer(answers, "concern_area") or []

    if "Tax Filing" in concerns:
        questions.extend(_tax_followups(answers))
    if "Immigration" in concerns:
        questions.extend(_immigration_followups(answers))
    if "Corporate Compliance" in concerns:
        questions.extend(_corporate_followups(answers))

    # Timeline urgency (cross-cutting)
    timeline = _get_answer(answers, "timeline_urgency")
    if isinstance(timeline, dict) and timeline.get("date"):
        questions.append(
            "What's currently blocking you from meeting this deadline? "
            "Understanding the blocker helps us prioritize the right documents."
        )

    return questions
