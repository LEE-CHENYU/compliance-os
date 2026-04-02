"""Test follow-up question generation — track-separated logic."""

from compliance_os.web.services.followup import generate_followups


def test_nr_with_1040_triggers_amendment_question():
    answers = [
        {"question_key": "concern_area", "answer": ["Tax Filing"]},
        {"question_key": "tax_residency_status", "answer": "Nonresident alien"},
        {"question_key": "tax_prior_filings", "answer": ["1040"]},
    ]
    questions = generate_followups(answers)
    assert any("1040" in q and ("amend" in q.lower() or "resident" in q.lower()) for q in questions)


def test_tax_entities_without_cpa_triggers_question():
    answers = [
        {"question_key": "concern_area", "answer": ["Tax Filing"]},
        {"question_key": "tax_entities", "answer": [{"name": "My LLC"}]},
        {"question_key": "existing_help", "answer": ["Lawyer"]},
    ]
    questions = generate_followups(answers)
    assert any("entity" in q.lower() or "business" in q.lower() for q in questions)


def test_f1_cpt_triggers_dso_question():
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "F-1"},
        {"question_key": "imm_subdomain", "answer": ["CPT/OPT authorization"]},
    ]
    questions = generate_followups(answers)
    assert any("dso" in q.lower() or "i-20" in q.lower() for q in questions)


def test_green_card_naturalization_asks_travel():
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "Green Card"},
        {"question_key": "imm_subdomain", "answer": ["Naturalization"]},
    ]
    questions = generate_followups(answers)
    assert any("naturalization" in q.lower() or "residence" in q.lower() for q in questions)


def test_no_answers_returns_empty():
    questions = generate_followups([])
    assert questions == []


def test_immigration_only_no_tax_followups():
    """Immigration-only concerns should not generate tax follow-ups."""
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "H-1B"},
        {"question_key": "imm_subdomain", "answer": ["Petition filing"]},
    ]
    questions = generate_followups(answers)
    # Should not mention 1040, FBAR, or tax residency
    assert not any("1040" in q or "fbar" in q.lower() for q in questions)
