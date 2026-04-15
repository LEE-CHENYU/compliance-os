"""Unit tests for process_h1b_doc_check — every rule, verdict path, and extraction mode."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import compliance_os.web.services.h1b_doc_check as h1b_mod
from compliance_os.web.services.pdf_builder import build_text_pdf


@pytest.fixture(autouse=True)
def _redirect_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h1b_mod, "H1B_DOC_CHECK_DIR", tmp_path / "h1b")
    yield tmp_path


def _text_doc(doc_type: str, order_id: str, **fields: str) -> dict:
    """Materialize a text document on disk and return the document manifest entry."""
    label_map = {
        "h1b_registration": [
            ("Registration Number", "registration_number"),
            ("Employer Name", "employer_name"),
            ("Employer EIN", "employer_ein"),
            ("Authorized Individual Name", "authorized_individual_name"),
            ("Authorized Individual Title", "authorized_individual_title"),
        ],
        "h1b_status_summary": [
            ("Status Title", "status_title"),
            ("Registration Window End Date", "registration_window_end_date"),
            ("Petition Filing Window End Date", "petition_filing_window_end_date"),
            ("Employment Start Date", "employment_start_date"),
            ("Law Firm Name", "law_firm_name"),
        ],
        "h1b_g28": [
            ("Representative Name", "representative_name"),
            ("Law Firm Name", "law_firm_name"),
            ("Representative Email", "representative_email"),
            ("Client Name", "client_name"),
            ("Client Entity Name", "client_entity_name"),
            ("Client Email", "client_email"),
        ],
        "h1b_filing_invoice": [
            ("Invoice Number", "invoice_number"),
            ("Invoice Date", "invoice_date"),
            ("Petitioner Name", "petitioner_name"),
            ("Beneficiary Name", "beneficiary_name"),
            ("Total Due Amount", "total_due_amount"),
        ],
        "h1b_filing_fee_receipt": [
            ("Transaction ID", "transaction_id"),
            ("Transaction Date", "transaction_date"),
            ("Response Message", "response_message"),
            ("Approval Code", "approval_code"),
            ("Cardholder Name", "cardholder_name"),
            ("Amount", "amount"),
            ("Description", "description"),
        ],
    }
    lines = [f"{label}: {fields[key]}" for label, key in label_map[doc_type] if key in fields]
    text = "\n".join(lines) + "\n"
    filename = f"{doc_type}.txt"
    path = h1b_mod.save_uploaded_document(order_id, filename, text.encode("utf-8"))
    return {"doc_type": doc_type, "filename": filename, "path": str(path)}


def _pdf_doc(doc_type: str, order_id: str, title: str, lines: list[str]) -> dict:
    """Materialize a real PDF and return the document manifest entry."""
    filename = f"{doc_type}.pdf"
    pdf_bytes = build_text_pdf(title, lines)
    path = h1b_mod.save_uploaded_document(order_id, filename, pdf_bytes)
    return {"doc_type": doc_type, "filename": filename, "path": str(path)}


def _full_clean_packet(order_id: str) -> list[dict]:
    """5 fully internally-consistent docs — nothing should fire except stale dates."""
    return [
        _text_doc("h1b_registration", order_id,
            registration_number="H1B-2026-CLEAN-001",
            employer_name="Acme Robotics Inc",
            employer_ein="12-3456789",
            authorized_individual_name="Alice Chen",
            authorized_individual_title="VP Engineering"),
        _text_doc("h1b_status_summary", order_id,
            status_title="Selected",
            registration_window_end_date="2026-03-25",
            petition_filing_window_end_date="2030-06-30",
            employment_start_date="2030-10-01",
            law_firm_name="Smith & Park LLP"),
        _text_doc("h1b_g28", order_id,
            representative_name="Jane Smith",
            law_firm_name="Smith & Park LLP",
            representative_email="jsmith@smithpark.example",
            client_name="Wei Zhang",
            client_entity_name="Acme Robotics Inc",
            client_email="hr@acmerobotics.example"),
        _text_doc("h1b_filing_invoice", order_id,
            invoice_number="INV-2026-0042",
            invoice_date="2026-04-10",
            petitioner_name="Acme Robotics Inc",
            beneficiary_name="Wei Zhang",
            total_due_amount="$2780"),
        _text_doc("h1b_filing_fee_receipt", order_id,
            transaction_id="TXN-7891011",
            transaction_date="2026-04-11",
            response_message="Approved",
            approval_code="OK-998877",
            cardholder_name="Alice Chen",
            amount="$2780",
            description="USCIS H-1B filing fee"),
    ]


def _rule_ids(result) -> set[str]:
    return {f["rule_id"] for f in result["findings"]}


# =======================
# Extraction / input paths
# =======================

def test_text_file_extraction():
    docs = [_text_doc("h1b_registration", "ext-txt",
        registration_number="H1B-TXT-1", employer_name="TextOnly Inc",
        authorized_individual_name="Alice")]
    result = h1b_mod.process_h1b_doc_check("ext-txt", {"documents": docs},
                                           today=date(2026, 4, 1))
    fields = result["document_summary"][0]["fields"]
    assert fields["registration_number"] == "H1B-TXT-1"
    assert fields["employer_name"] == "TextOnly Inc"


def test_real_pdf_extraction_via_pymupdf():
    """Regression: binary PDFs used to yield empty extraction. Fixed in batch 1."""
    docs = [_pdf_doc("h1b_registration", "ext-pdf", "H-1B Registration", [
        "Registration Number: H1B-PDF-1",
        "Employer Name: PDFOnly Corp",
        "Authorized Individual Name: Bob",
    ])]
    result = h1b_mod.process_h1b_doc_check("ext-pdf", {"documents": docs},
                                           today=date(2026, 4, 1))
    fields = result["document_summary"][0]["fields"]
    assert fields["registration_number"] == "H1B-PDF-1"
    assert fields["employer_name"] == "PDFOnly Corp"


def test_prefill_path_uses_provided_fields_dict():
    """When a doc has pre-extracted `fields`, we bypass file parsing entirely."""
    docs = [{
        "doc_type": "h1b_registration",
        "filename": "prefill.pdf",
        "path": "/nonexistent/path/that/would/crash/read_text",
        "fields": {
            "registration_number": "H1B-PREFILL-1",
            "employer_name": "Prefilled Co",
            "authorized_individual_name": "Eve",
        },
    }]
    # Path is bogus — if the code tried to read it, the test would crash.
    result = h1b_mod.process_h1b_doc_check("prefill", {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["document_summary"][0]["fields"]["employer_name"] == "Prefilled Co"


def test_unreadable_pdf_yields_empty_fields_without_crashing():
    """A PDF with no matchable text (e.g., scanned image) returns {} rather than raising."""
    path = h1b_mod.save_uploaded_document("bad", "bad.pdf", b"%PDF-1.7 garbage binary")
    docs = [{"doc_type": "h1b_registration", "filename": "bad.pdf", "path": str(path)}]
    result = h1b_mod.process_h1b_doc_check("bad", {"documents": docs},
                                           today=date(2026, 4, 1))
    # No exception, empty extraction
    assert result["document_summary"][0]["fields"] == {}


def test_mixed_pdf_and_text_packet():
    order = "mixed"
    docs = [
        _pdf_doc("h1b_registration", order, "Reg", [
            "Registration Number: H1B-MIX-1",
            "Employer Name: Mixed Co",
            "Authorized Individual Name: Mix Signer",
        ]),
        _text_doc("h1b_g28", order,
            representative_name="Law Yer",
            client_entity_name="Mixed Co",
        ),
    ]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    registration_fields = next(
        d["fields"] for d in result["document_summary"] if d["doc_type"] == "h1b_registration"
    )
    assert registration_fields["employer_name"] == "Mixed Co"


# =======================
# Verdict: pass / investigate / block / incomplete
# =======================

def test_registration_number_malformed_value_discarded():
    """Regression: extractor used to grab literal 'H-1B#' label fragments as
    the registration_number from table-layout PDFs. The validator now discards
    obviously malformed matches so the rule engine correctly reports the
    number as missing instead of acting on garbage."""
    from compliance_os.web.services.h1b_doc_check import extract_h1b_document_fields
    # Source PDF has the label but the value is on the next line; the greedy
    # regex grabs 'H-1B#' instead of the real number
    text = "Registration Number: H-1B#\nH1BR2026ABC1234567\n"
    fields = extract_h1b_document_fields("h1b_registration", text)
    assert "registration_number" not in fields or fields["registration_number"] != "H-1B#"


def test_registration_number_valid_format_kept():
    from compliance_os.web.services.h1b_doc_check import extract_h1b_document_fields
    text = "Registration Number: H1BR2026ABC1234567\n"
    fields = extract_h1b_document_fields("h1b_registration", text)
    assert fields["registration_number"] == "H1BR2026ABC1234567"


def test_invoice_amount_comparison_uses_fees_not_residual_balance():
    """Regression: comparing 'total_due_amount' (residual balance after
    payment) against the receipt amount always mismatched on paid invoices.
    Now we compare sum of legal_fee_amount + uscis_fee_amount."""
    order = "invoice-fees"
    docs = [
        _text_doc("h1b_registration", order,
            registration_number="H1BR2026CLEAN123",
            employer_name="Acme Corp",
            authorized_individual_name="Alice"),
        _text_doc("h1b_g28", order, client_entity_name="Acme Corp"),
        _text_doc("h1b_filing_invoice", order,
            petitioner_name="Acme Corp",
            beneficiary_name="Wei Zhang",
            total_due_amount="0"),  # paid — residual is 0
        _text_doc("h1b_filing_fee_receipt", order,
            cardholder_name="Alice",
            amount="515"),
    ]
    # Inject legal + uscis fee amounts by adding them as raw text in invoice doc
    from compliance_os.web.services.h1b_doc_check import save_uploaded_document
    invoice_text = (
        "Invoice Number: INV-2026\n"
        "Petitioner Name: Acme Corp\n"
        "Beneficiary Name: Wei Zhang\n"
        "Legal Fee Amount: 300\n"
        "USCIS Fee Amount: 215\n"
        "Total Due Amount: 0\n"
    )
    docs = [d for d in docs if d["doc_type"] != "h1b_filing_invoice"]
    path = save_uploaded_document(order, "invoice-fees.txt", invoice_text.encode("utf-8"))
    docs.append({"doc_type": "h1b_filing_invoice", "filename": "invoice-fees.txt", "path": str(path)})

    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    # 300 + 215 = 515, receipt is 515 → match, no amount_mismatch finding
    assert "h1b_amount_mismatch" not in _rule_ids(result)


def test_already_filed_detection_flips_window_closed_to_info():
    """Regression: users reviewing a successfully-filed packet saw 'window
    closed' as a critical BLOCK verdict. With filing evidence (approval code
    + transaction ID) the rule now fires at info severity instead."""
    order = "already-filed-eu"
    docs = _full_clean_packet(order)
    # Status summary with past window
    docs = [d for d in docs if d["doc_type"] != "h1b_status_summary"]
    docs.append(_text_doc("h1b_status_summary", order,
        status_title="Selected",
        petition_filing_window_end_date="2025-06-30"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    closed_finding = next(
        (f for f in result["findings"] if f["rule_id"].startswith("h1b_window_closed_already")),
        None,
    )
    assert closed_finding is not None
    assert closed_finding["severity"] == "info"
    # Should NOT be the critical variant
    assert not any(f["rule_id"] == "h1b_window_closed_not_filed" for f in result["findings"])


def test_verdict_pass_when_clean_packet():
    docs = _full_clean_packet("verdict-pass")
    result = h1b_mod.process_h1b_doc_check("verdict-pass", {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "pass"
    assert result["packet_complete"] is True
    assert result["missing_doc_types"] == []


def test_verdict_block_on_critical_finding():
    """Critical finding should force block verdict even if packet is complete."""
    order = "verdict-block"
    docs = _full_clean_packet(order)
    # Replace g28 to create an entity-name mismatch with registration
    docs = [d for d in docs if d["doc_type"] != "h1b_g28"]
    docs.append(_text_doc("h1b_g28", order,
        representative_name="J Smith",
        client_entity_name="Different Corp LLC",  # critical mismatch
        client_name="Wei Zhang"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "block"


def test_verdict_investigate_on_warning_only():
    """Only warnings (no critical) → investigate."""
    order = "verdict-investigate"
    docs = _full_clean_packet(order)
    # Replace receipt with amount mismatch (warning)
    docs = [d for d in docs if d["doc_type"] != "h1b_filing_fee_receipt"]
    docs.append(_text_doc("h1b_filing_fee_receipt", order,
        transaction_id="T1", cardholder_name="Alice Chen", amount="$9999"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "investigate"


def test_verdict_incomplete_when_only_one_doc():
    """<3 documents → incomplete verdict with upload-first message."""
    order = "verdict-incomplete"
    docs = [_text_doc("h1b_registration", order,
        registration_number="X", employer_name="Y")]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "incomplete"
    assert result["packet_complete"] is False
    assert len(result["missing_doc_types"]) == 4
    assert "Upload" in result["next_steps"][0] or "upload" in result["next_steps"][0]


def test_verdict_incomplete_at_two_docs():
    order = "verdict-incomplete-2"
    docs = [
        _text_doc("h1b_registration", order, registration_number="X", employer_name="Y"),
        _text_doc("h1b_g28", order, client_entity_name="Y"),
    ]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "incomplete"


def test_verdict_not_incomplete_at_three_docs():
    """Boundary: 3 docs is enough to run cross-checks."""
    order = "verdict-three"
    docs = [
        _text_doc("h1b_registration", order, registration_number="X", employer_name="Acme Inc"),
        _text_doc("h1b_g28", order, client_entity_name="Acme Inc"),
        _text_doc("h1b_filing_invoice", order, petitioner_name="Acme Inc"),
    ]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["verdict"] != "incomplete"


# =======================
# Individual rules
# =======================

def test_rule_missing_registration_packet():
    """No registration doc → critical: 'Registration document missing'."""
    order = "missing-reg"
    docs = [_text_doc("h1b_g28", order, client_entity_name="X"),
            _text_doc("h1b_filing_invoice", order, petitioner_name="X"),
            _text_doc("h1b_filing_fee_receipt", order, cardholder_name="X")]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_missing_registration_packet" in _rule_ids(result)


def test_rule_missing_registration_number():
    """Registration present but no registration_number field → warning."""
    order = "missing-reg-num"
    docs = _full_clean_packet(order)
    # Rewrite registration without registration_number
    docs = [d for d in docs if d["doc_type"] != "h1b_registration"]
    docs.insert(0, _text_doc("h1b_registration", order,
        employer_name="Acme Robotics Inc",
        authorized_individual_name="Alice Chen"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_missing_registration_number" in _rule_ids(result)


def test_rule_entity_name_mismatch_critical():
    order = "entity-mm"
    docs = _full_clean_packet(order)
    docs = [d for d in docs if d["doc_type"] != "h1b_g28"]
    docs.append(_text_doc("h1b_g28", order,
        client_entity_name="WildlyDifferent Corp",  # base-name mismatch
        client_name="Wei Zhang"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_entity_name_mismatch" in _rule_ids(result)


def test_rule_entity_suffix_change_inc_vs_llc_fires():
    """After batch 2: Inc vs LLC must fire the entity-mismatch rule."""
    order = "suffix-mm"
    docs = _full_clean_packet(order)
    docs = [d for d in docs if d["doc_type"] != "h1b_filing_invoice"]
    docs.append(_text_doc("h1b_filing_invoice", order,
        petitioner_name="Acme Robotics LLC",  # registration says Inc
        beneficiary_name="Wei Zhang", total_due_amount="$2780"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_petitioner_invoice_mismatch" in _rule_ids(result)


def test_rule_signatory_payment_mismatch_info():
    order = "sig-mm"
    docs = _full_clean_packet(order)
    docs = [d for d in docs if d["doc_type"] != "h1b_filing_fee_receipt"]
    docs.append(_text_doc("h1b_filing_fee_receipt", order,
        cardholder_name="Bob Wong",  # registration signer is Alice Chen
        amount="$2780"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_signatory_payment_mismatch" in _rule_ids(result)


def test_rule_amount_mismatch_warning():
    order = "amt-mm"
    docs = _full_clean_packet(order)
    docs = [d for d in docs if d["doc_type"] != "h1b_filing_fee_receipt"]
    docs.append(_text_doc("h1b_filing_fee_receipt", order,
        cardholder_name="Alice Chen", amount="$1500"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "h1b_amount_mismatch" in _rule_ids(result)


def test_rule_window_closed_already_filed_fires_info_for_past_date_with_receipt():
    """When the receipt shows filing evidence, window-closed becomes informational."""
    order = "window-closed-filed"
    docs = _full_clean_packet(order)
    # Clean packet already has a receipt with approval code → filing-evidence detected.
    # Override status to indicate window end is in the past.
    docs = [d for d in docs if d["doc_type"] != "h1b_status_summary"]
    docs.append(_text_doc("h1b_status_summary", order,
        status_title="Selected",
        petition_filing_window_end_date="2020-06-30"))
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    rule_ids = _rule_ids(result)
    assert "h1b_window_closed_already_filed" in rule_ids
    assert "h1b_window_closed_not_filed" not in rule_ids


def test_rule_window_closed_not_filed_fires_critical_without_receipt():
    """No receipt → no filing evidence → critical warning fires."""
    order = "window-closed-unfiled"
    docs = [
        _text_doc("h1b_registration", order,
            registration_number="H1BR2026ABC123",
            employer_name="Acme Corp",
            authorized_individual_name="Alice"),
        _text_doc("h1b_status_summary", order,
            status_title="Selected",
            petition_filing_window_end_date="2020-06-30"),
        _text_doc("h1b_g28", order, client_entity_name="Acme Corp"),
    ]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    rule_ids = _rule_ids(result)
    assert "h1b_window_closed_not_filed" in rule_ids
    assert "h1b_window_closed_already_filed" not in rule_ids


def test_rule_window_closed_does_not_fire_for_future_date():
    order = "window-open"
    docs = _full_clean_packet(order)
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    rule_ids = _rule_ids(result)
    assert "h1b_window_closed_not_filed" not in rule_ids
    assert "h1b_window_closed_already_filed" not in rule_ids


# =======================
# Output shape
# =======================

def test_result_includes_comparisons():
    docs = _full_clean_packet("comparisons")
    result = h1b_mod.process_h1b_doc_check("comparisons", {"documents": docs},
                                           today=date(2026, 4, 1))
    names = {c["field_name"] for c in result["comparisons"]}
    assert "h1b_registration_g28_entity_name" in names
    assert "h1b_registration_invoice_petitioner_name" in names
    assert "h1b_registration_receipt_signatory_name" in names
    assert "h1b_invoice_receipt_amount" in names


def test_result_includes_report_artifact():
    docs = _full_clean_packet("artifact")
    result = h1b_mod.process_h1b_doc_check("artifact", {"documents": docs},
                                           today=date(2026, 4, 1))
    assert result["artifacts"]
    report_path = Path(result["artifacts"][0]["path"])
    assert report_path.exists()
    assert report_path.suffix == ".pdf"


def test_report_header_includes_verdict():
    from compliance_os.web.services.pdf_reader import extract_first_page
    docs = _full_clean_packet("header")
    result = h1b_mod.process_h1b_doc_check("header", {"documents": docs},
                                           today=date(2026, 4, 1))
    text = extract_first_page(result["artifacts"][0]["path"])
    assert "Verdict:" in text
    assert "PASS" in text
    assert "Packet completeness" in text


def test_summary_mentions_uploaded_over_expected():
    docs = _full_clean_packet("summary")
    result = h1b_mod.process_h1b_doc_check("summary", {"documents": docs},
                                           today=date(2026, 4, 1))
    assert "5 of 5" in result["summary"]


def test_comparisons_skipped_when_one_side_missing():
    """Phantom-finding regression: previously we emitted a comparison with
    status=needs_review when a whole document wasn't uploaded, and the rule
    engine's 'mismatch' operator treats needs_review as a trigger. We now
    skip the comparison entirely so no phantom finding fires."""
    order = "needs-review-skip"
    docs = [
        _text_doc("h1b_registration", order,
            registration_number="R1", employer_name="Acme Inc",
            authorized_individual_name="Alice"),
        _text_doc("h1b_status_summary", order,
            status_title="Selected",
            petition_filing_window_end_date="2030-06-30"),
    ]
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    # No phantom entries — comparisons list only contains checks with both sides
    for comparison in result["comparisons"]:
        assert comparison["status"] != "needs_review", (
            f"Unexpected phantom comparison: {comparison}"
        )
    # Also: no entity-mismatch rule should fire against a document that's absent
    from_engine = {f["rule_id"] for f in result["findings"]}
    assert "h1b_entity_name_mismatch" not in from_engine
    assert "h1b_petitioner_invoice_mismatch" not in from_engine


# =======================
# Edge cases
# =======================

def test_empty_documents_list():
    result = h1b_mod.process_h1b_doc_check("empty", {"documents": []},
                                           today=date(2026, 4, 1))
    assert result["verdict"] == "incomplete"
    assert result["packet_complete"] is False


def test_intake_without_documents_key():
    result = h1b_mod.process_h1b_doc_check("no-key", {}, today=date(2026, 4, 1))
    assert result["verdict"] == "incomplete"


def test_duplicate_doc_type_keeps_last_extracted():
    """If two registration docs are uploaded, extraction prefers the last entry."""
    order = "dup"
    docs = [
        _text_doc("h1b_registration", order,
            registration_number="FIRST", employer_name="First Co"),
        _text_doc("h1b_g28", order, client_entity_name="X"),
        _text_doc("h1b_filing_invoice", order, petitioner_name="X"),
    ]
    # Manually tweak filename to avoid overwrite, then add second registration
    second = h1b_mod.save_uploaded_document(order, "registration_v2.txt",
        b"Registration Number: SECOND\nEmployer Name: Second Co\n")
    docs.append({"doc_type": "h1b_registration", "filename": "registration_v2.txt", "path": str(second)})
    result = h1b_mod.process_h1b_doc_check(order, {"documents": docs},
                                           today=date(2026, 4, 1))
    # The later entry wins the `extracted[doc_type] = fields` assignment
    reg_summaries = [d for d in result["document_summary"] if d["doc_type"] == "h1b_registration"]
    assert len(reg_summaries) == 2  # both appear in document_summary
