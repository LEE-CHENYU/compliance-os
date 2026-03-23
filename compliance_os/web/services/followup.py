"""Generate targeted follow-up questions from discovery answers."""


def _get_answer(answers: list[dict], key: str):
    for a in answers:
        if a.get("question_key") == key:
            return a.get("answer")
    return None


def generate_followups(answers: list[dict]) -> list[str]:
    """Produce follow-up questions based on wizard answers. Rule-based, not LLM."""
    questions: list[str] = []
    if not answers:
        return questions

    residency = _get_answer(answers, "residency_status")
    prior_filings = _get_answer(answers, "prior_filings") or []
    entities = _get_answer(answers, "entities") or []
    existing_help = _get_answer(answers, "existing_help") or []
    timeline = _get_answer(answers, "timeline_urgency")

    # F-1/H-1B with resident return
    if residency in ("F-1", "H-1B") and "1040" in prior_filings:
        questions.append(
            "You filed a Form 1040, but as an F-1/H-1B holder you may qualify as a "
            "nonresident alien. Was this filing prepared by a CPA, or self-prepared?"
        )

    # Entities without CPA
    if entities and "CPA/Accountant" not in existing_help:
        questions.append(
            "Who handles the tax filings for your business entity? "
            "Entity returns (e.g., Form 5472) have strict penalties if missed."
        )

    # Urgent deadline
    if isinstance(timeline, dict) and timeline.get("date"):
        questions.append(
            "What's currently blocking you from meeting this deadline? "
            "Understanding the blocker helps us prioritize the right documents."
        )

    # F-1 with entities
    if residency == "F-1" and entities:
        questions.append(
            "As an F-1 student, owning a business entity can have immigration implications. "
            "Has your immigration attorney reviewed your entity ownership?"
        )

    return questions
