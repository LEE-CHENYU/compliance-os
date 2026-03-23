"""Test follow-up question generation from discovery answers."""

from compliance_os.web.services.followup import generate_followups


def test_f1_with_1040_triggers_nr_question():
    answers = [
        {"question_key": "residency_status", "answer": "F-1"},
        {"question_key": "prior_filings", "answer": ["1040"]},
    ]
    questions = generate_followups(answers)
    assert any("nonresident" in q.lower() or "1040" in q for q in questions)


def test_entities_without_cpa_triggers_question():
    answers = [
        {"question_key": "entities", "answer": [{"name": "My LLC"}]},
        {"question_key": "existing_help", "answer": ["Lawyer"]},
    ]
    questions = generate_followups(answers)
    assert any("tax" in q.lower() and ("entity" in q.lower() or "business" in q.lower()) for q in questions)


def test_no_answers_returns_empty():
    questions = generate_followups([])
    assert questions == []
