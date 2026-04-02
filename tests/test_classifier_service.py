"""Test lightweight document classification."""

from io import BytesIO
from zipfile import ZipFile

import compliance_os.web.services.extractor as extractor
import compliance_os.web.services.pdf_reader as pdf_reader
from compliance_os.web.services.classifier import (
    PATH_EXCEPTION_PATTERNS,
    classify_file,
    classify_filename,
    classify_text,
    classifier_generality_report,
)


def _build_docx_bytes(paragraphs: list[str]) -> bytes:
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}</w:body>
</w:document>
"""
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buf.getvalue()


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


def test_h1b_registration_filename_pattern_does_not_match_retainer_documents():
    assert classify_filename("/tmp/legal/immigration/h1b_retainer_hibee.pdf").doc_type != "h1b_registration"


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


def test_batch_06_root_identity_and_education_classification():
    assert classify_filename("/tmp/visa.jpeg").doc_type == "visa_stamp"
    assert classify_filename("/tmp/SSN.jpg").doc_type == "social_security_card"
    assert classify_filename("/tmp/Student ID.jpg").doc_type == "student_id"
    assert classify_filename("/tmp/Driver’s license （中）.jpeg").doc_type == "drivers_license"
    assert classify_filename("/tmp/diploma.pdf").doc_type == "degree_certificate"
    assert classify_filename("/tmp/Transcript for Waseda University.pdf").doc_type == "transcript"
    assert classify_filename("/tmp/李宸宇_本科生英文成绩单.pdf").doc_type == "transcript"


def test_batch_07_to_10_filename_classification_regressions():
    assert classify_filename("/tmp/employment/VCV/vcv_full_time.pdf").doc_type == "employment_letter"
    assert classify_filename("/tmp/employment/VCV/vcv_internship.pdf").doc_type == "employment_letter"
    assert classify_filename("/tmp/stem opt/letter/stemoptemployerletter.pdf").doc_type == "employment_letter"
    assert (
        classify_filename("/tmp/stem opt/request/Requests for Employment and Immigration Support& Support.pdf").doc_type
        == "support_request"
    )
    assert (
        classify_filename("/tmp/BSGC/Filing/Archive/EIN Individual Request - Instructions.pdf").doc_type
        == "ein_application_instructions"
    )
    assert classify_filename("/tmp/BSGC/Filing/Archive/CP575Notice_1684523211250.pdf").doc_type == "ein_letter"
    assert (
        classify_filename("/tmp/BSGC/Filing/Archive/EIN Individual Request - Online Application 2.pdf").doc_type
        == "ein_application"
    )
    assert (
        classify_filename("/tmp/BSGC/Filing/EIN Individual Request - Online Application.pdf").doc_type
        == "ein_application"
    )
    assert (
        classify_filename("/tmp/BSGC/Filing/Archive/Wyoming-Single-Member-LLC-Operating-Agreement.pdf").doc_type
        == "operating_agreement"
    )
    assert classify_filename("/tmp/BSGC/Filing/Consent.pdf").doc_type == "registered_agent_consent"
    assert classify_filename("/tmp/BSGC/Filing/Tax-interview.pdf").doc_type == "tax_interview"
    assert classify_filename("/tmp/BSGC/TDA1186.pdf").doc_type == "bank_account_application"
    assert classify_filename("/tmp/BSGC/lawdepot.com-EMPLOYMENT CONTRACT.pdf").doc_type == "employment_contract"
    assert classify_filename("/tmp/Tax/2024/Year-End Summary - 2024_2025-03-07_619.PDF").doc_type == "annual_account_summary"
    assert classify_filename("/tmp/Tax/2025/US_W-4_2024.pdf").doc_type == "w4"
    assert classify_filename("/tmp/H1b Petition/Employee/Passport/IMG_0991大.jpeg").doc_type == "passport"
    assert classify_filename("/tmp/H1b Petition/Employee/EAD/IMG_0996.jpeg").doc_type == "ead"
    assert classify_filename("/tmp/H1b Petition/Employee/Transcript/40697019_eTranscript.pdf").doc_type == "transcript"


def test_batch_11_to_15_filename_classification_regressions():
    assert classify_filename("/tmp/学历认证.pdf").doc_type == "degree_certificate"
    assert classify_filename("/tmp/公司信息/营业执照(老).jpg").doc_type == "business_license"
    assert classify_filename("/tmp/公司信息/支付宝支付服务合同.pdf").doc_type == "payment_service_agreement"
    assert classify_filename("/tmp/公司信息/银行账户.JPG").doc_type == "bank_account_record"
    assert classify_filename("/tmp/公司信息/alipayPublicKey_RSA2-new.txt").doc_type == "public_key"
    assert classify_filename("/tmp/BSGC/shopify_recovery_codes.txt").doc_type == "recovery_codes"
    assert classify_filename("/tmp/Yangtze Capital/3-5-26 - null - Initial Filing - Yangtze Capital.pdf").doc_type == "company_filing"
    assert classify_filename("/tmp/i20/I20/Admission Letter.pdf").doc_type == "admission_letter"
    assert classify_filename("/tmp/i20/ciam_continued_attendence.pdf").doc_type == "enrollment_verification"
    assert classify_filename("/tmp/Medical/Medicard02.png").doc_type == "insurance_card"
    assert classify_filename("/tmp/Medical/N250714184955_Template012_235756780_03_12_2025_03_05_11_EN.pdf").doc_type == "insurance_record"
    assert classify_filename("/tmp/Personal Info Archive/New Member Packet - Welcome.pdf").doc_type == "membership_welcome_packet"
    assert classify_filename("/tmp/Personal Info Archive/南京居住证明.pdf").doc_type == "residence_certificate"
    assert classify_filename("/tmp/Mom ID/Weixin Image_20260209173713_337_168.jpg").doc_type == "identity_document"
    assert classify_filename("/tmp/CV & Cover Letters/CV260306/Chenyu Li Resume_H1b.pdf").doc_type == "resume"
    assert classify_filename("/tmp/CV & Cover Letters/CV241028/OXY Stock Pitch.pdf").doc_type == "work_sample"


def test_batch_16_to_20_filename_classification_regressions():
    assert classify_filename("/tmp/employment/Claudius/12 month (page-5) .pdf").doc_type == "final_evaluation"
    assert classify_filename("/tmp/employment/Claudius/Wage Theft Prevention Act Notice_Signed.pdf").doc_type == "wage_notice"
    assert classify_filename("/tmp/stem opt/Order Confirmation.pdf").doc_type == "order_confirmation"
    assert classify_filename("/tmp/stem opt/i983/Instructions/I-983samplefilled.pdf").doc_type == "immigration_reference"
    assert classify_filename("/tmp/stem opt/retain the proof.png").doc_type == "filing_confirmation"
    assert classify_filename("/tmp/Lease/Collection/Debt Clearence.pdf").doc_type == "debt_clearance_letter"
    assert classify_filename("/tmp/Invoice/Payment Receipt-2.pdf").doc_type == "payment_receipt"
    assert classify_filename("/tmp/Tax/2024/bank_document_-2819197501764181827.pdf").doc_type == "bank_statement"
    assert classify_filename("/tmp/CV & Cover Letters/transcript&diploma/JLPT_N1.pdf").doc_type == "language_test_certificate"
    assert classify_filename("/tmp/i20/ciam_transfer_pending.pdf").doc_type == "transfer_pending_letter"


def test_batch_56_accounting_bank_and_transfer_classification_regressions():
    assert (
        classify_filename(
            "/tmp/bank_statements/citibank/citibank_llc_chk5039_20240409_20250929.csv"
        ).doc_type
        == "bank_statement"
    )
    assert (
        classify_filename(
            "/tmp/bank_statements/schwab/schwab_llc_xxx239_20250225_20251006.csv"
        ).doc_type
        == "bank_statement"
    )
    assert (
        classify_filename(
            "/tmp/bank_statements/schwab/statements/schwab_brokerage_stmt_xxx239_2025-07.pdf"
        ).doc_type
        == "bank_statement"
    )
    assert classify_filename("/tmp/bank_statements/citizens_payment_options_2958.pdf").doc_type == "payment_options_notice"
    assert (
        classify_filename(
            "/tmp/bank_statements/wire_transfers_2026/EWB_ChenChunjiang_to_EastWestBank_030226.JPG"
        ).doc_type
        == "wire_transfer_record"
    )


def test_batch_57_accounting_legal_and_h1b_packet_classification_regressions():
    assert classify_filename("/tmp/legal/corporate/Fee Agreement - Signed Electronically.pdf").doc_type == "legal_services_agreement"
    assert classify_filename("/tmp/legal/corporate/Yangtze Capital 2nd EIN Cancellation Letter.pdf").doc_type == "entity_notice"
    assert (
        classify_filename("/tmp/legal/immigration/bsgc_h1b_registration_beneficiaries_031026.csv").doc_type
        == "h1b_registration_roster"
    )
    assert (
        classify_filename("/tmp/legal/immigration/h1b_2026_lottery_registration.docx").doc_type
        == "h1b_registration"
    )
    assert classify_filename("/tmp/legal/immigration/h1b_cap_legal_services_agreement.pdf").doc_type == "legal_services_agreement"
    assert classify_filename("/tmp/legal/immigration/h1b_retainer_hibee.pdf").doc_type == "legal_services_agreement"
    assert classify_filename("/tmp/legal/immigration/yangtze_capital_ftb_withholding_notice_022526.pdf").doc_type == "tax_notice"
    assert (
        classify_text("Legal Services Agreement Attorney Client H-1B registration services").doc_type
        == "legal_services_agreement"
    )


def test_batch_58_accounting_school_and_status_classification_regressions():
    assert classify_filename("/tmp/legal/immigration/i20_affidavit_financial_support.pdf").doc_type == "financial_support_affidavit"
    assert (
        classify_filename("/tmp/outgoing/ciam/CIAM Fall II 2025 Introduction (10.22.2025).pdf").doc_type
        == "school_policy_notice"
    )
    assert (
        classify_filename("/tmp/outgoing/ciam/CIAM Internship Courses (INT501 & INT599) 10.22.2025.pdf").doc_type
        == "school_policy_notice"
    )
    assert classify_filename("/tmp/outgoing/ciam/INT501 INT599 Application Non-CPT.pdf").doc_type == "school_policy_notice"
    assert classify_filename("/tmp/tax/2025/1098T_CIAM_2025.pdf").doc_type == "tuition_statement"
    assert classify_filename("/tmp/tmp/dl_cn.jpeg").doc_type == "drivers_license"
    assert (
        classify_text("Form 1098-T Tuition Statement Payments received for qualified tuition and related expenses").doc_type
        == "tuition_statement"
    )


def test_brokerage_csv_text_does_not_false_positive_as_drivers_license():
    text = (
        '"Date","Action","Symbol","Description","Quantity","Price","Fees & Comm","Amount"\n'
        '"09/22/2025","MoneyLink Transfer","","Tfr Citibank NA, CHENYU LI","","","","$30000.00"\n'
    )

    result = classify_text(text)

    assert result.doc_type == "bank_statement"
    assert result.doc_type != "drivers_license"


def test_batch_26_to_30_filename_and_text_classification_regressions():
    assert (
        classify_filename("/tmp/CV & Cover Letters/CV230217/李宸宇18652053798_230718.pdf").doc_type
        == "resume"
    )
    assert classify_filename("/tmp/Lease/Fang, Yuchen_293947.pdf").doc_type == "lease"
    assert (
        classify_filename("/tmp/ICDATAx2725 Confirmation of paper modification 7.pdf").doc_type
        == "filing_confirmation"
    )
    assert (
        classify_filename("/tmp/employment/Yangtze Capital/CIAM_CPT_App_Li_Chenyu.pdf").doc_type
        == "cpt_application"
    )
    assert (
        classify_filename("/tmp/employment/Bitsync/Gmail - Urgent_ Compliance with STEM OPT Requirements.pdf").doc_type
        == "support_request"
    )
    assert (
        classify_text(
            "Dear DSO, I am writing to address an urgent matter regarding my employment and the "
            "documentation requirements under the STEM OPT program."
        ).doc_type
        == "support_request"
    )
    assert (
        classify_filename("/tmp/employment/CliniPulse/Attorney Letter to Chenyu Li-03212025.pdf").doc_type
        == "employment_correspondence"
    )
    assert (
        classify_text(
            "Please be advised that we represent CliniPulse LLC. This letter constitutes our "
            "response to your demand for unpaid wages and withdraws the offer letter."
        ).doc_type
        == "employment_correspondence"
    )
    assert (
        classify_filename("/tmp/employment/JZ/Contract & Signed Letter - JZ Capital LLC.pdf").doc_type
        == "employment_contract"
    )
    assert (
        classify_text(
            "We are delighted to share the following employment documents with you. "
            "Review and e-sign your employment documents ahead of your start date."
        ).doc_type
        == "employment_contract"
    )
    assert (
        classify_text(
            "Tiger Cloud, LLC OPT Employer letter. This is to certify that Chenyu Li is employed "
            "and this letter is issued in conjunction with employment authorization."
        ).doc_type
        == "employment_letter"
    )


def test_batch_31_to_35_filename_classification_regressions():
    assert (
        classify_filename("/tmp/employment/Rai/6ee18925-9e2b-40e2-b442-a956c4100c28.pdf").doc_type
        == "non_disclosure_agreement"
    )
    assert (
        classify_filename("/tmp/employment/Rai/Request for PTO and Floating Holiday Utilization 924  1011.pdf").doc_type
        == "employment_correspondence"
    )
    assert classify_filename("/tmp/employment/VCV/Signature Pages.pdf").doc_type == "signature_page"
    assert classify_filename("/tmp/employment/Wolff & Li/blank_stock_check_payment.pdf").doc_type == "check_image"
    assert (
        classify_filename(
            "/tmp/employment/Rai/Glyde Digital Announces RAI Inc. Secures $45 Million in Strategic Investments to Advance XR and AI Innovation _ Morningstar.pdf"
        ).doc_type
        == "news_article"
    )
    assert classify_filename("/tmp/Tax/2024/document.pdf").doc_type == "1099"
    assert classify_filename("/tmp/Yangtze Capital/Yangtze Capital.pdf").doc_type == "ein_application"
    assert classify_filename("/tmp/employment/Rai/Screenshot from Justwork.png").doc_type == "employment_screenshot"
    assert (
        classify_filename("/tmp/employment/Bitsync/Will Communications/IMG_9455.PNG").doc_type
        == "employment_screenshot"
    )
    assert (
        classify_filename("/tmp/employment/Bitsync/ChatExport_2024-12-14/images/media_call.png").doc_type
        == "chat_export_asset"
    )
    assert (
        classify_filename("/tmp/employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_game@2x.png").doc_type
        == "chat_export_asset"
    )
    assert (
        classify_filename("/tmp/CV & Cover Letters/transcript&diploma/20210713112836-0001.pdf").doc_type
        == "degree_certificate"
    )
    assert classify_filename("/tmp/CV & Cover Letters/transcript&diploma/IMG_0514.JPG").doc_type == "degree_certificate"
    assert classify_filename("/tmp/i20/I20/38911625468472_.pic.png").doc_type == "i20"
    assert classify_filename("/tmp/i20/I20/I-20 Travel.rtfd/EmailTracker.cfm.jpg").doc_type == "i20"
    assert classify_filename("/tmp/Veeup.cc/网站备案.png").doc_type == "company_filing"
    assert classify_filename("/tmp/授权书/29431747363841_.pic.jpg").doc_type == "company_filing"
    assert classify_filename("/tmp/treasury pass.png").doc_type == "account_security_setup"
    assert classify_filename("/tmp/新春竹_对公账户.pic.jpg").doc_type == "bank_account_record"


def test_single_reference_does_not_force_i94_or_ead_classification():
    assert classify_text("Enter your I-94 visa number.") .doc_type is None
    assert classify_text("Recipient's date of birth and federal tax withheld.") .doc_type is None


def test_new_batch_16_to_20_patterns_do_not_overclassify_generic_documents():
    assert classify_filename("/tmp/statement_of_purpose.pdf").doc_type is None
    assert classify_text("Please retain this for your records after submission.").doc_type is None


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


def test_batch_36_to_40_filename_and_text_classification_regressions():
    assert classify_filename("/tmp/BSGC/Docs/IMG_0991.jpeg").doc_type == "passport"
    assert classify_filename("/tmp/BSGC/Docs/IMG_1708.jpeg").doc_type == "identity_document"
    assert classify_filename("/tmp/BSGC/Docs/IMG_1792.jpg").doc_type == "social_security_card"
    assert classify_filename("/tmp/Personal Info Archive/IMG_1675.pdf").doc_type == "social_security_record"
    assert classify_filename("/tmp/Personal Info Archive/IMG_1725.pdf").doc_type == "drivers_license"
    assert classify_filename("/tmp/IMG_3721 Medium.jpeg").doc_type == "identity_document"
    assert classify_filename("/tmp/WechatIMG219.jpeg").doc_type == "identity_document"
    assert classify_filename("/tmp/Photo.jpg").doc_type == "profile_photo"
    assert classify_filename("/tmp/CV & Cover Letters/CV230217/R0015961 (1).jpeg").doc_type == "profile_photo"
    assert classify_filename("/tmp/Happyhunting Screenshot/51745372824_.pic.jpg").doc_type == "employment_screenshot"
    assert classify_filename("/tmp/Weixin Image_2025-07-02_213642_922.png").doc_type == "system_configuration_screenshot"
    assert classify_filename("/tmp/スクリーンショット 2025-04-17 午前11.49.19.png").doc_type == "account_security_setup"
    assert classify_filename("/tmp/Veeup.cc/WechatIMG13.jpg").doc_type == "system_configuration_screenshot"
    assert classify_filename("/tmp/Veeup.cc/WechatIMG14.jpg").doc_type == "company_filing"
    assert (
        classify_filename(
            "/tmp/Invitation to the projectWorld Congress in Computer Science Computer Engineering and Applied Computing.pdf"
        ).doc_type
        == "event_invitation"
    )
    assert classify_filename("/tmp/employment/Bitsync/IMG_9347.PNG").doc_type == "employment_screenshot"
    assert (
        classify_filename("/tmp/employment/Bitsync/Will Communications/IMG_9471.PNG").doc_type
        == "employment_screenshot"
    )
    assert classify_filename("/tmp/stem opt/Tiger Cloud, LLC - New York. NY.pdf").doc_type == "employment_letter"
    assert (
        classify_filename("/tmp/stem opt/i983/vcv/Signature Pages.pdf").doc_type
        == "signature_page"
    )
    assert (
        classify_text("SSNAP Printout for Replacement Social Security Number Card Number Holder Name").doc_type
        == "social_security_record"
    )
    assert classify_text("IPv4 DNS NetBIOS Realtek").doc_type == "system_configuration_screenshot"
    assert (
        classify_text("Meteor Support Invitation to the project World Congress in Computer Science").doc_type
        == "event_invitation"
    )


def test_batch_51_to_55_docx_filename_and_text_classification_regressions():
    assert (
        classify_filename("/tmp/CV & Cover Letters/Chenyu Li Cover Letter - World Bank.docx").doc_type
        == "cover_letter"
    )
    assert (
        classify_filename(
            "/tmp/CV & Cover Letters/CV260325/cover_letters/Hebbia - Solutions Engineer - Cover Letter.docx"
        ).doc_type
        == "cover_letter"
    )
    assert (
        classify_text(
            "Cover Letter Dear hiring manager at BlackRock, please consider my qualifications. "
            "I am interested in the Portfolio Analytics position."
        ).doc_type
        == "cover_letter"
    )
    assert (
        classify_filename("/tmp/CV & Cover Letters/CV240712/Samples/GTM Action Items.docx").doc_type
        == "work_sample"
    )
    assert (
        classify_filename("/tmp/CV & Cover Letters/CV241028/Samples/Intel Guady.docx").doc_type
        == "work_sample"
    )
    assert (
        classify_filename(
            "/tmp/H1b Petition/Employee/H-1B Part I_Registration Worksheet and Document Checklist_Employee.docx"
        ).doc_type
        == "h1b_registration_worksheet"
    )
    assert (
        classify_text(
            "H-1B Registration Worksheet and Document Checklist for Petitioning Employer "
            "Required Company Information Required Company Documentation"
        ).doc_type
        == "h1b_registration_worksheet"
    )
    assert (
        classify_filename("/tmp/BSGC/Contract of Employment - BD Manager.docx").doc_type
        == "employment_contract"
    )
    assert (
        classify_filename(
            "/tmp/stem opt/request/Issues Requiring Employer Assistance & Support.docx"
        ).doc_type
        == "support_request"
    )


def test_general_path_patterns_cover_unseen_archive_variants():
    assert (
        classify_filename("/tmp/employment/Bitsync/ChatExport_2024-12-14 (99)/images/section_web@2x.png").doc_type
        == "chat_export_asset"
    )
    assert classify_filename("/tmp/employment/Bitsync/IMG_9999.PNG").doc_type == "employment_screenshot"
    assert (
        classify_filename("/tmp/employment/Bitsync/Will Communications/IMG_12345.PNG").doc_type
        == "employment_screenshot"
    )
    assert (
        classify_filename("/tmp/employment/Example Co/WhatsApp Image 2026-04-01 at 3.21.00 PM.jpeg").doc_type
        == "employment_screenshot"
    )
    assert (
        classify_filename("/tmp/CV & Cover Letters/CV250101/R0019999 (12).jpeg").doc_type
        == "profile_photo"
    )
    assert (
        classify_filename("/tmp/Invitation to the Example World Congress on Applied Computing.pdf").doc_type
        == "event_invitation"
    )


def test_text_file_content_can_classify_identifier_record(tmp_path):
    path = tmp_path / "token.txt"
    path.write_text("51da1642a056795f8d9717cb60704640")

    result = classify_file(str(path), "text/plain", allow_ocr=False)

    assert result.doc_type == "identifier_record"
    assert result.source == "text"


def test_docx_content_can_classify_resume(tmp_path):
    path = tmp_path / "candidate_profile.docx"
    path.write_bytes(
        _build_docx_bytes(
            [
                "Chenyu Li Resume",
                "Experience",
                "Education",
                "Skills",
            ]
        )
    )

    result = classify_file(
        str(path),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        allow_ocr=False,
    )

    assert result.doc_type == "resume"
    assert result.source == "text"


def test_docx_content_can_classify_cover_letter(tmp_path):
    path = tmp_path / "cover_letter.docx"
    path.write_bytes(
        _build_docx_bytes(
            [
                "Cover Letter",
                "Dear hiring manager at Hebbia,",
                "Please consider my qualifications.",
                "I am interested in the Solutions Engineer position.",
            ]
        )
    )

    result = classify_file(
        str(path),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        allow_ocr=False,
    )

    assert result.doc_type == "cover_letter"
    assert result.source == "filename"


def test_classifier_generality_report_keeps_path_exceptions_scoped():
    report = classifier_generality_report()

    assert report["path_exception_pattern_count"] < report["path_context_pattern_count"]
    assert "chat_export_asset" not in PATH_EXCEPTION_PATTERNS
    assert "employment_screenshot" not in PATH_EXCEPTION_PATTERNS
    assert "event_invitation" not in PATH_EXCEPTION_PATTERNS
    assert set(PATH_EXCEPTION_PATTERNS).issubset(
        {
            "account_security_setup",
            "company_filing",
            "drivers_license",
            "ein_application",
            "employment_letter",
            "final_evaluation",
            "identity_document",
            "passport",
            "profile_photo",
            "social_security_card",
            "social_security_record",
            "system_configuration_screenshot",
        }
    )
