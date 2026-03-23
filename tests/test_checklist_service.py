"""Test document checklist generation from discovery answers."""

from compliance_os.web.services.checklist import generate_checklist


def test_tax_concern_generates_tax_slots():
    answers = [
        {"step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"]},
        {"step": "prior_filings", "question_key": "prior_filings", "answer": ["1040"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "w2_latest" in keys
    assert "prior_return_2024" in keys


def test_immigration_concern_generates_immigration_slots():
    answers = [
        {"step": "concern_area", "question_key": "concern_area", "answer": ["Immigration"]},
        {"step": "residency_status", "question_key": "residency_status", "answer": "F-1"},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "i20" in keys
    assert "passport_id_page" in keys
    assert "i94" in keys


def test_entities_generate_per_entity_slots():
    answers = [
        {"step": "concern_area", "question_key": "concern_area", "answer": ["Corporate Compliance"]},
        {"step": "entities", "question_key": "entities", "answer": [
            {"name": "My LLC", "type": "LLC", "state": "WY", "ein": "12-3456789"}
        ]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "my-llc_formation" in keys
    assert "my-llc_ein_letter" in keys


def test_other_slot_always_present():
    answers = [
        {"step": "concern_area", "question_key": "concern_area", "answer": ["Other"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "other" in keys
