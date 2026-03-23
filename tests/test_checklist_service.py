"""Test document checklist generation — track-separated logic."""

from compliance_os.web.services.checklist import generate_checklist


def test_tax_track_generates_tax_slots():
    answers = [
        {"question_key": "concern_area", "answer": ["Tax Filing"]},
        {"question_key": "tax_residency_status", "answer": "Nonresident alien"},
        {"question_key": "tax_prior_filings", "answer": ["1040-NR"]},
        {"question_key": "tax_income_sources", "answer": ["W-2 employment"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    groups = [s.group for s in slots]
    assert "tax_w2" in keys
    assert "tax_prior_return_recent" in keys
    assert "tax_8843" in keys  # NR-specific
    assert "tax_passport" in keys  # NR needs passport for SPT
    # Should NOT have immigration slots
    assert not any(k.startswith("imm_") for k in keys)
    # All groups should be Tax-related
    assert all("Tax" in g or "General" in g for g in groups)


def test_immigration_f1_generates_student_slots():
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "F-1"},
        {"question_key": "imm_subdomain", "answer": ["CPT/OPT authorization"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "imm_i20" in keys
    assert "imm_passport" in keys
    assert "imm_i94" in keys
    assert "imm_cpt_letter" in keys
    # Should NOT have tax slots
    assert not any(k.startswith("tax_") for k in keys)


def test_immigration_h1b_generates_petition_slots():
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "H-1B"},
        {"question_key": "imm_subdomain", "answer": ["Petition filing"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "imm_i129" in keys
    assert "imm_lca" in keys


def test_green_card_no_visa_tracking_slots():
    """Green Card holders should NOT get I-20, visa stamp, or I-94 slots."""
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "Green Card"},
        {"question_key": "imm_subdomain", "answer": ["Naturalization"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "imm_i20" not in keys
    assert "imm_visa_stamp" not in keys
    assert "imm_i94" not in keys
    assert "imm_green_card" in keys
    assert "imm_n400_docs" in keys


def test_citizen_minimal_slots():
    """Citizens should only get records-related slots, not visa slots."""
    answers = [
        {"question_key": "concern_area", "answer": ["Immigration"]},
        {"question_key": "imm_visa_category", "answer": "U.S. Citizen"},
        {"question_key": "imm_subdomain", "answer": ["Records request"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "imm_passport" not in keys
    assert "imm_visa_stamp" not in keys
    assert "imm_i94" not in keys
    assert "imm_foia_docs" in keys


def test_corporate_track_generates_entity_slots():
    answers = [
        {"question_key": "concern_area", "answer": ["Corporate Compliance"]},
        {"question_key": "corp_entities", "answer": [
            {"name": "My LLC", "type": "LLC", "state": "WY", "ein": "12-3456789"}
        ]},
        {"question_key": "corp_obligations", "answer": ["Annual report"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "corp_my-llc_formation" in keys
    assert "corp_my-llc_ein" in keys
    assert "corp_my-llc_annual" in keys


def test_multiple_concerns_separate_tracks():
    """Selecting Tax + Immigration generates both track's slots, separated."""
    answers = [
        {"question_key": "concern_area", "answer": ["Tax Filing", "Immigration"]},
        {"question_key": "tax_residency_status", "answer": "Nonresident alien"},
        {"question_key": "tax_income_sources", "answer": ["W-2 employment"]},
        {"question_key": "imm_visa_category", "answer": "F-1"},
        {"question_key": "imm_subdomain", "answer": []},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    groups = [s.group for s in slots]
    # Has both tax and immigration slots
    assert any(k.startswith("tax_") for k in keys)
    assert any(k.startswith("imm_") for k in keys)
    # Groups are clearly separated
    tax_groups = [g for g in groups if "Tax" in g]
    imm_groups = [g for g in groups if "Immigration" in g]
    assert len(tax_groups) > 0
    assert len(imm_groups) > 0


def test_nr_no_fbar_slots():
    """Nonresident aliens should NOT get FBAR/8938 slots."""
    answers = [
        {"question_key": "concern_area", "answer": ["Tax Filing"]},
        {"question_key": "tax_residency_status", "answer": "Nonresident alien"},
        {"question_key": "tax_income_sources", "answer": ["Foreign income"]},
    ]
    slots = generate_checklist(answers)
    keys = [s.key for s in slots]
    assert "tax_fbar_records" not in keys
    assert "tax_8938_records" not in keys
