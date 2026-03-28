"""Test lightweight document classification."""

import compliance_os.web.services.extractor as extractor
import compliance_os.web.services.pdf_reader as pdf_reader
from compliance_os.web.services.classifier import classify_file, classify_filename, classify_text


def test_w2_classification():
    text = "Wage and Tax Statement 2024 Form W-2"
    result = classify_text(text)
    assert result.doc_type == "w2"


def test_i20_classification():
    text = "Certificate of Eligibility for Nonimmigrant Student Status Form I-20"
    result = classify_text(text)
    assert result.doc_type == "i20"


def test_i983_classification():
    text = "TRAINING PLAN FOR STEM OPT STUDENTS Form I-983"
    result = classify_text(text)
    assert result.doc_type == "i983"


def test_employment_letter_classification():
    text = "Employment Offer Letter We are pleased to offer you the position of Data Analyst"
    result = classify_text(text)
    assert result.doc_type == "employment_letter"


def test_ead_classification():
    text = "Employment Authorization Document USCIS# 123456789 Card Expires 2027-10-01"
    result = classify_text(text)
    assert result.doc_type == "ead"


def test_unknown_text_returns_none():
    text = "Random document with no recognizable patterns"
    result = classify_text(text)
    assert result.doc_type is None


def test_tax_return_classification():
    text = "U.S. Nonresident Alien Income Tax Return Form 1040-NR"
    result = classify_text(text)
    assert result.doc_type == "tax_return"


def test_filename_classification():
    result = classify_filename("/tmp/Chenyu_i983 Form_100124_ink_signed.pdf")
    assert result.doc_type == "i983"


def test_filename_classification_with_upload_prefix():
    result = classify_filename("/tmp/1234_passport.jpeg")
    assert result.doc_type == "passport"


def test_batch_02_filename_classification():
    assert classify_filename("/tmp/Articles of Organization.pdf").doc_type == "articles_of_organization"
    assert classify_filename("/tmp/CertOfGoodStanding.pdf").doc_type == "certificate_of_good_standing"
    assert classify_filename("/tmp/1042S - 2025.PDF").doc_type == "1042s"
    assert classify_filename("/tmp/sublease agreement.pdf").doc_type == "lease"


def test_health_coverage_application_text_classification():
    text = (
        "www.CoveredCA.com Application date 10/16/2025 "
        "Who is the Primary Contact for your household?"
    )
    result = classify_text(text)
    assert result.doc_type == "health_coverage_application"


def test_batch_03_text_classification():
    assert classify_text("Pay Period Start Pay Period End Pay Date Net Pay").doc_type == "paystub"
    assert classify_text("Employment Eligibility Verification Form I-9 USCIS").doc_type == "i9"
    assert classify_text("E-Verify Case Number Company Information Employee Information").doc_type == "e_verify_case"
    assert classify_text("Application For Employment Authorization USCIS Form I-765").doc_type == "i765"
    assert classify_text("USCIS H-1B Registration Registration Number").doc_type == "h1b_registration"
    assert classify_text(
        "H-1B Status Requirements for H-1B visa status How to File for New H-1B visa status"
    ).doc_type == "h1b_status_summary"


def test_batch_03_filename_classification():
    assert classify_filename("/tmp/Paystub20240112.pdf").doc_type == "paystub"
    assert classify_filename("/tmp/I9.pdf").doc_type == "i9"
    assert classify_filename("/tmp/E-Verify Case Processing.pdf").doc_type == "e_verify_case"
    assert classify_filename("/tmp/I-765-stem opt.pdf").doc_type == "i765"
    assert classify_filename("/tmp/H-1BR (1).pdf").doc_type == "h1b_registration"
    assert (
        classify_filename("/tmp/FY 2026 H-1B Status Overview_for employee_Cindy-1.pdf").doc_type
        == "h1b_status_summary"
    )


def test_batch_04_h1b_petition_classification():
    assert (
        classify_text(
            "H-1B Status How to File for New H-1B visa status "
            "Required Documents for Filing for H-1B visa status"
        ).doc_type
        == "h1b_status_summary"
    )
    assert (
        classify_text(
            "H-1B \u7533\u8bf7\u624b\u518c \u5982\u4f55\u7533\u8bf7\u65b0\u7684 H-1B \u7b7e\u8bc1"
        ).doc_type
        == "h1b_status_summary"
    )
    assert classify_text("Notice of Entry of Appearance as Attorney or Accredited Representative DHS Form G-28").doc_type == "h1b_g28"
    assert classify_text("INVOICE H-1B Cap Petition H-1B Registration Filing Fee").doc_type == "h1b_filing_invoice"
    assert classify_text("Transaction Information Response Message Approval Code H1B registration").doc_type == "h1b_filing_fee_receipt"

    assert classify_filename("/tmp/G-28 (1).pdf").doc_type == "h1b_g28"
    assert classify_filename("/tmp/Invoice_Part I_LI, Chenyu_paid.pdf").doc_type == "h1b_filing_invoice"
    assert classify_filename("/tmp/Transaction #45217993.pdf").doc_type == "h1b_filing_fee_receipt"


def test_batch_05_identity_travel_archive_classification():
    assert classify_filename("/tmp/I-20_Li_Chenyu_ FA 2025.pdf").doc_type == "i20"
    assert classify_filename("/tmp/I94 - 1019 print.pdf").doc_type == "i94"
    assert classify_filename("/tmp/passport.jpeg").doc_type == "passport"
    assert classify_filename("/tmp/EAD_expired.pdf").doc_type == "ead"
    assert classify_filename("/tmp/Form_W-2_Tax_Year_2024.pdf").doc_type == "w2"
    assert classify_filename("/tmp/2024_TaxReturn.pdf").doc_type == "tax_return"
    assert classify_filename("/tmp/1042S - 2025_2026-03-10_619.PDF").doc_type == "1042s"
    assert (
        classify_text(
            "Certificate of Eligibility for Nonimmigrant Student Status Form I-20 "
            "Most recent DSO travel signature date"
        ).doc_type
        == "i20"
    )


def test_single_reference_does_not_force_i94_or_ead_classification():
    assert classify_text("Enter your I-94 visa number.") .doc_type is None
    assert classify_text("Recipient's date of birth and federal tax withheld.") .doc_type is None


def test_classify_file_uses_ocr_fallback(monkeypatch, tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"fake")

    monkeypatch.setattr(pdf_reader, "extract_first_page", lambda _: "")
    monkeypatch.setattr(
        extractor,
        "extract_pdf_text",
        lambda _: "TRAINING PLAN FOR STEM OPT STUDENTS Form I-983",
    )

    result = classify_file(str(path), "application/pdf")

    assert result.doc_type == "i983"


def test_classify_file_can_skip_ocr_fallback(monkeypatch, tmp_path):
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"fake")

    monkeypatch.setattr(pdf_reader, "extract_first_page", lambda _: "")
    monkeypatch.setattr(
        extractor,
        "extract_pdf_text",
        lambda _: "TRAINING PLAN FOR STEM OPT STUDENTS Form I-983",
    )

    result = classify_file(str(path), "application/pdf", allow_ocr=False)

    assert result.doc_type is None


def test_ocr_reference_terms_do_not_force_i94_passport_or_ein_classification(monkeypatch, tmp_path):
    path = tmp_path / "questionnaire.pdf"
    path.write_bytes(b"fake")

    monkeypatch.setattr(pdf_reader, "extract_first_page", lambda _: "")
    monkeypatch.setattr(
        extractor,
        "extract_pdf_text",
        lambda _: (
            "Onboarding worksheet asks for Most Recent I-94, Class of Admission, "
            "Admit Until Date, Passport Number, Nationality, and Employer Identification Number."
        ),
    )

    result = classify_file(str(path), "application/pdf")

    assert result.doc_type is None


def test_ocr_i94_still_classifies_when_arrival_departure_anchor_present(monkeypatch, tmp_path):
    path = tmp_path / "travel_scan.pdf"
    path.write_bytes(b"fake")

    monkeypatch.setattr(pdf_reader, "extract_first_page", lambda _: "")
    monkeypatch.setattr(
        extractor,
        "extract_pdf_text",
        lambda _: "Arrival/Departure Record Most Recent I-94 Class of Admission F1 Admit Until Date D/S",
    )

    result = classify_file(str(path), "application/pdf")

    assert result.doc_type == "i94"
    assert result.source == "ocr"


def test_ocr_ein_letter_requires_cp575_anchor(monkeypatch, tmp_path):
    path = tmp_path / "ein_notice.pdf"
    path.write_bytes(b"fake")

    monkeypatch.setattr(pdf_reader, "extract_first_page", lambda _: "")
    monkeypatch.setattr(
        extractor,
        "extract_pdf_text",
        lambda _: "Employer Identification Number (EIN) has been assigned per IRS CP 575 notice.",
    )

    result = classify_file(str(path), "application/pdf")

    assert result.doc_type == "ein_letter"
    assert result.source == "ocr"
