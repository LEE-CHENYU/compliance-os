"""Tests for Guardian check flow API routes."""
from datetime import datetime, timedelta, timezone

import compliance_os.web.routers.extraction as extraction_mod
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import Base as BaseV2, CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.document_intake import ResolvedDocumentType
from compliance_os.web.services.extractor import TextExtractionResult


@pytest.fixture
def test_engine():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from compliance_os.web.models.database import Base as OldBase
    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_check(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "stem_opt", "years_in_us": 3}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["track"] == "stem_opt"
    assert data["answers"]["stage"] == "stem_opt"
    assert data["status"] == "intake"


def test_get_check(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {}})
    check_id = resp.json()["id"]
    resp = client.get(f"/api/checks/{check_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == check_id


def test_get_check_not_found(client):
    resp = client.get("/api/checks/nonexistent")
    assert resp.status_code == 404


def test_update_check_answers(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "opt"}})
    check_id = resp.json()["id"]
    resp = client.patch(f"/api/checks/{check_id}", json={"answers": {"years_in_us": 5}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answers"]["stage"] == "opt"
    assert data["answers"]["years_in_us"] == 5


def test_comparisons_endpoint(client, db_session):
    # Create a check with pre-populated extracted fields
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    # Add i983 document with extracted fields
    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    db_session.add(doc_a)
    db_session.flush()
    for name, val in [("job_title", "Data Analyst"), ("employer_name", "Acme Corp"), ("compensation", "85000")]:
        db_session.add(ExtractedFieldRow(document_id=doc_a.id, field_name=name, field_value=val, confidence=0.9))

    # Add employment letter with extracted fields
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add(doc_b)
    db_session.flush()
    for name, val in [("job_title", "Business Ops Associate"), ("employer_name", "Acme Corp"), ("compensation", "85000")]:
        db_session.add(ExtractedFieldRow(document_id=doc_b.id, field_name=name, field_value=val, confidence=0.9))

    db_session.commit()

    # Run comparison
    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    comparisons = resp.json()
    assert len(comparisons) > 0

    # Job title should mismatch
    job_title = next(c for c in comparisons if c["field_name"] == "job_title")
    assert job_title["status"] == "mismatch"

    # Employer name should match
    employer = next(c for c in comparisons if c["field_name"] == "employer_name")
    assert employer["status"] == "match"

    # Compensation should match
    comp = next(c for c in comparisons if c["field_name"] == "compensation")
    assert comp["status"] == "match"


def test_data_room_comparisons_consume_batch_03_fields(client, db_session):
    check = CheckRow(track="data_room", status="extracted", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    docs = {
        "paystub": DocumentRow(
            check_id=check.id,
            doc_type="paystub",
            filename="paystub.pdf",
            file_path="/tmp/paystub.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "i9": DocumentRow(
            check_id=check.id,
            doc_type="i9",
            filename="i9.pdf",
            file_path="/tmp/i9.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "e_verify_case": DocumentRow(
            check_id=check.id,
            doc_type="e_verify_case",
            filename="everify.pdf",
            file_path="/tmp/everify.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "i765": DocumentRow(
            check_id=check.id,
            doc_type="i765",
            filename="i765.pdf",
            file_path="/tmp/i765.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "h1b_registration": DocumentRow(
            check_id=check.id,
            doc_type="h1b_registration",
            filename="h1b-registration.pdf",
            file_path="/tmp/h1b-registration.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
    }
    db_session.add_all(docs.values())
    db_session.flush()

    extracted = {
        "paystub": {
            "employer_name": "Justworks Employment Group LLC",
            "pay_period_end": "2024-11-30",
            "net_pay": "2500.00",
        },
        "i9": {
            "employee_name": "Chenyu Li",
            "employee_first_day_of_employment": "2025-03-17",
            "citizenship_status": "A noncitizen authorized to work",
        },
        "e_verify_case": {
            "case_number": "2025079225618BC",
            "case_status": "Employment Authorized",
            "employee_name": "Chenyu Li",
            "employee_first_day_of_employment": "2025-03-17",
        },
        "i765": {
            "applicant_name": "Chenyu Li",
            "eligibility_category": "C03C",
            "application_reason": "Renewal of permission to accept employment",
        },
        "h1b_registration": {
            "registration_number": "DERIVED-H1BR-F4CEF8CFA191",
            "employer_name": "Bamboo Shoot Growth Capital LLC",
            "employer_ein": "93-1924106",
        },
    }

    for doc_type, field_map in extracted.items():
        for field_name, field_value in field_map.items():
            db_session.add(
                ExtractedFieldRow(
                    document_id=docs[doc_type].id,
                    field_name=field_name,
                    field_value=field_value,
                    confidence=0.9,
                )
            )
    db_session.commit()

    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    comparisons = {entry["field_name"]: entry for entry in resp.json()}

    assert comparisons["paystub_pay_period_end"]["value_b"] == "2024-11-30"
    assert comparisons["i9_employee_first_day_of_employment"]["value_b"] == "2025-03-17"
    assert comparisons["everify_case_number"]["value_b"] == "2025079225618BC"
    assert comparisons["i765_eligibility_category"]["value_b"] == "C03C"
    assert comparisons["h1b_registration_number"]["value_b"] == "DERIVED-H1BR-F4CEF8CFA191"
    assert comparisons["i9_everify_employee_name"]["status"] == "match"
    assert comparisons["i9_everify_first_day_of_employment"]["status"] == "match"


def test_data_room_comparisons_consume_batch_04_fields(client, db_session):
    check = CheckRow(track="data_room", status="extracted", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    docs = {
        "h1b_registration": DocumentRow(
            check_id=check.id,
            doc_type="h1b_registration",
            filename="h1b-registration.pdf",
            file_path="/tmp/h1b-registration.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "h1b_status_summary": DocumentRow(
            check_id=check.id,
            doc_type="h1b_status_summary",
            filename="h1b-status-overview.pdf",
            file_path="/tmp/h1b-status-overview.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "h1b_g28": DocumentRow(
            check_id=check.id,
            doc_type="h1b_g28",
            filename="g-28.pdf",
            file_path="/tmp/g-28.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "h1b_filing_invoice": DocumentRow(
            check_id=check.id,
            doc_type="h1b_filing_invoice",
            filename="invoice.pdf",
            file_path="/tmp/invoice.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "h1b_filing_fee_receipt": DocumentRow(
            check_id=check.id,
            doc_type="h1b_filing_fee_receipt",
            filename="receipt.pdf",
            file_path="/tmp/receipt.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
    }
    db_session.add_all(docs.values())
    db_session.flush()

    extracted = {
        "h1b_registration": {
            "registration_number": "DERIVED-H1BR-F4CEF8CFA191",
            "employer_name": "Bamboo Shoot Growth Capital LLC",
            "authorized_individual_name": "Chenyu Li",
        },
        "h1b_status_summary": {
            "status_title": "H-1B Status",
            "registration_window_end_date": "2025-03-20",
            "petition_filing_window_end_date": "2025-06-30",
        },
        "h1b_g28": {
            "representative_name": "Xinzi Chen",
            "client_entity_name": "Bamboo Shoot Growth Capital LLC",
        },
        "h1b_filing_invoice": {
            "invoice_number": "H-1B#",
            "total_due_amount": "515.00",
            "beneficiary_name": "Chenyu Li",
            "petitioner_name": "Bamboo Shoot Growth Capital LLC",
        },
        "h1b_filing_fee_receipt": {
            "transaction_id": "45217993",
            "response_message": "APPROVAL",
            "amount": "850.00",
            "cardholder_name": "Chenyu Li",
        },
    }

    for doc_type, field_map in extracted.items():
        for field_name, field_value in field_map.items():
            db_session.add(
                ExtractedFieldRow(
                    document_id=docs[doc_type].id,
                    field_name=field_name,
                    field_value=field_value,
                    confidence=0.9,
                )
            )
    db_session.commit()

    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    comparisons = {entry["field_name"]: entry for entry in resp.json()}

    assert comparisons["h1b_status_title"]["value_b"] == "H-1B Status"
    assert comparisons["h1b_registration_window_end_date"]["value_b"] == "2025-03-20"
    assert comparisons["h1b_g28_representative_name"]["value_b"] == "Xinzi Chen"
    assert comparisons["h1b_invoice_total_due_amount"]["value_b"] == "515.00"
    assert comparisons["h1b_receipt_transaction_id"]["value_b"] == "45217993"
    assert comparisons["h1b_registration_g28_entity_name"]["status"] == "match"
    assert comparisons["h1b_registration_invoice_petitioner_name"]["status"] == "match"
    assert comparisons["h1b_registration_receipt_signatory_name"]["status"] == "match"
    assert comparisons["h1b_invoice_receipt_beneficiary_name"]["status"] == "match"


def test_data_room_comparisons_consume_batch_05_fields(client, db_session):
    check = CheckRow(track="data_room", status="extracted", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    docs = {
        "i20": DocumentRow(
            check_id=check.id,
            doc_type="i20",
            filename="i20.pdf",
            file_path="/tmp/i20.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "i94": DocumentRow(
            check_id=check.id,
            doc_type="i94",
            filename="i94.pdf",
            file_path="/tmp/i94.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "passport": DocumentRow(
            check_id=check.id,
            doc_type="passport",
            filename="passport.jpeg",
            file_path="/tmp/passport.jpeg",
            file_size=100,
            mime_type="image/jpeg",
        ),
        "ead": DocumentRow(
            check_id=check.id,
            doc_type="ead",
            filename="ead.pdf",
            file_path="/tmp/ead.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "w2": DocumentRow(
            check_id=check.id,
            doc_type="w2",
            filename="w2.pdf",
            file_path="/tmp/w2.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "tax_return": DocumentRow(
            check_id=check.id,
            doc_type="tax_return",
            filename="tax_return.pdf",
            file_path="/tmp/tax_return.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
        "1042s": DocumentRow(
            check_id=check.id,
            doc_type="1042s",
            filename="1042s.pdf",
            file_path="/tmp/1042s.pdf",
            file_size=100,
            mime_type="application/pdf",
        ),
    }
    db_session.add_all(docs.values())
    db_session.flush()

    extracted = {
        "i20": {
            "student_name": "Chenyu Li",
            "program_end_date": "2025-12-16",
            "travel_signature_date": "2025-02-20",
        },
        "i94": {
            "class_of_admission": "F-1",
            "most_recent_entry_date": "2025-03-04",
            "admit_until_date": "D/S",
        },
        "passport": {
            "full_name": "Chenyu Li",
            "date_of_birth": "1998-09-18",
            "expiration_date": "2032-11-15",
        },
        "ead": {
            "full_name": "Chenyu Li",
            "date_of_birth": "1998-09-18",
            "card_expires_on": "2026-10-01",
        },
        "w2": {
            "employee_name": "Chenyu Li",
            "tax_year": "2024",
        },
        "tax_return": {
            "form_type": "1040",
            "tax_year": "2024",
        },
        "1042s": {
            "recipient_name": "Chenyu Li",
            "tax_year": "2024",
        },
    }

    for doc_type, field_map in extracted.items():
        for field_name, field_value in field_map.items():
            db_session.add(
                ExtractedFieldRow(
                    document_id=docs[doc_type].id,
                    field_name=field_name,
                    field_value=field_value,
                    confidence=0.9,
                )
            )
    db_session.commit()

    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    comparisons = {entry["field_name"]: entry for entry in resp.json()}

    assert comparisons["i20_student_name"]["value_b"] == "Chenyu Li"
    assert comparisons["i94_class_of_admission"]["value_b"] == "F-1"
    assert comparisons["passport_full_name"]["value_b"] == "Chenyu Li"
    assert comparisons["ead_card_expires_on"]["value_b"] == "2026-10-01"
    assert comparisons["w2_tax_year"]["value_b"] == "2024"
    assert comparisons["tax_return_form_type"]["value_b"] == "1040"
    assert comparisons["form_1042s_tax_year"]["value_b"] == "2024"

    assert comparisons["i20_passport_student_name"]["status"] == "match"
    assert comparisons["i20_ead_student_name"]["status"] == "match"
    assert comparisons["passport_ead_date_of_birth"]["status"] == "match"
    assert comparisons["passport_w2_employee_name"]["status"] == "match"
    assert comparisons["passport_1042s_recipient_name"]["status"] == "match"
    assert comparisons["w2_tax_return_tax_year"]["status"] == "match"
    assert comparisons["1042s_tax_return_tax_year"]["status"] == "match"
    assert comparisons["i94_i20_class_of_admission"]["status"] == "match"


def test_evaluate_endpoint(client, db_session):
    # Create check with comparisons already done
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt", "years_in_us": 3})
    db_session.add(check)
    db_session.flush()

    # Add documents + extracted fields (minimal)
    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    # Run compare first
    client.post(f"/api/checks/{check.id}/compare")

    # Run evaluate
    resp = client.post(f"/api/checks/{check.id}/evaluate")
    assert resp.status_code == 200
    findings = resp.json()
    assert isinstance(findings, list)


def test_data_room_evaluate_endpoint_uses_data_room_rules(client, db_session):
    check = CheckRow(track="data_room", status="extracted", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    passport = DocumentRow(
        check_id=check.id,
        doc_type="passport",
        filename="passport.jpeg",
        file_path="/tmp/passport.jpeg",
        file_size=100,
        mime_type="image/jpeg",
    )
    ead = DocumentRow(
        check_id=check.id,
        doc_type="ead",
        filename="ead.pdf",
        file_path="/tmp/ead.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    db_session.add_all([passport, ead])
    db_session.flush()
    db_session.add_all(
        [
            ExtractedFieldRow(
                document_id=passport.id,
                field_name="date_of_birth",
                field_value="1998-09-18",
                confidence=0.9,
            ),
            ExtractedFieldRow(
                document_id=ead.id,
                field_name="date_of_birth",
                field_value="1998-09-01",
                confidence=0.9,
            ),
        ]
    )
    db_session.commit()

    compare_resp = client.post(f"/api/checks/{check.id}/compare")
    assert compare_resp.status_code == 200

    evaluate_resp = client.post(f"/api/checks/{check.id}/evaluate")
    assert evaluate_resp.status_code == 200
    findings = evaluate_resp.json()

    assert any(finding["rule_id"] == "passport_ead_birthdate_mismatch" for finding in findings)


def test_followups_generated_from_mismatches(client, db_session):
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add_all([doc_a, doc_b])
    db_session.flush()

    # Add mismatched extracted fields
    db_session.add(ExtractedFieldRow(document_id=doc_a.id, field_name="job_title", field_value="Data Analyst", confidence=0.9))
    db_session.add(ExtractedFieldRow(document_id=doc_b.id, field_name="job_title", field_value="Marketing Lead", confidence=0.9))
    db_session.commit()

    # Compare
    client.post(f"/api/checks/{check.id}/compare")

    # Generate followups
    resp = client.post(f"/api/checks/{check.id}/followups")
    assert resp.status_code == 200
    followups = resp.json()
    assert len(followups) > 0
    assert any("job_title" in f["question_key"] for f in followups)


def test_compare_prefers_latest_document_version(client, db_session):
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    older = DocumentRow(
        check_id=check.id,
        doc_type="i983",
        filename="old_i983.pdf",
        file_path="/tmp/old_i983.pdf",
        file_size=100,
        mime_type="application/pdf",
        uploaded_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    newer = DocumentRow(
        check_id=check.id,
        doc_type="i983",
        filename="new_i983.pdf",
        file_path="/tmp/new_i983.pdf",
        file_size=100,
        mime_type="application/pdf",
        uploaded_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    letter = DocumentRow(
        check_id=check.id,
        doc_type="employment_letter",
        filename="letter.pdf",
        file_path="/tmp/letter.pdf",
        file_size=100,
        mime_type="application/pdf",
        uploaded_at=datetime.now(timezone.utc),
    )
    db_session.add_all([older, newer, letter])
    db_session.flush()

    db_session.add(ExtractedFieldRow(document_id=older.id, field_name="employer_name", field_value="Old Corp", confidence=0.9))
    db_session.add(ExtractedFieldRow(document_id=newer.id, field_name="employer_name", field_value="New Corp", confidence=0.9))
    db_session.add(ExtractedFieldRow(document_id=letter.id, field_name="employer_name", field_value="New Corp", confidence=0.9))
    db_session.commit()

    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    employer = next(c for c in resp.json() if c["field_name"] == "employer_name")
    assert employer["value_a"] == "New Corp"
    assert employer["status"] == "match"


def test_entity_type_comparison_flags_foreign_smllc_1040_as_needs_review(client, db_session):
    check = CheckRow(
        track="entity",
        status="extracted",
        answers={"entity_type": "smllc", "owner_residency": "on_visa"},
    )
    db_session.add(check)
    db_session.flush()

    tax_return = DocumentRow(
        check_id=check.id,
        doc_type="tax_return",
        filename="return.pdf",
        file_path="/tmp/return.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    db_session.add(tax_return)
    db_session.flush()
    db_session.add(ExtractedFieldRow(document_id=tax_return.id, field_name="form_type", field_value="1040", confidence=0.9))
    db_session.add(ExtractedFieldRow(document_id=tax_return.id, field_name="form_5472_present", field_value="False", confidence=0.9))
    db_session.commit()

    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    entity_type = next(c for c in resp.json() if c["field_name"] == "entity_type")
    assert entity_type["status"] == "needs_review"
    assert "single-member LLC" in entity_type["detail"]


def test_upload_sets_version_metadata(client, db_session):
    check_id = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "stem_opt"}}).json()["id"]

    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "employment_letter", "source_path": "/tmp/offer_v1.pdf"},
        files={"file": ("offer_v1.pdf", b"offer-v1", "application/pdf")},
    )
    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "employment_letter", "source_path": "/tmp/offer_v2.pdf"},
        files={"file": ("offer_v2.pdf", b"offer-v2", "application/pdf")},
    )

    db_session.expire_all()
    docs = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check_id)
        .order_by(DocumentRow.document_version.asc(), DocumentRow.id.asc())
        .all()
    )

    assert len(docs) == 2
    assert docs[0].document_family == "employment_letter"
    assert docs[0].document_series_key == "employment_letter"
    assert docs[0].document_version == 1
    assert docs[0].is_active is False
    assert docs[0].source_path == "/tmp/offer_v1.pdf"
    assert docs[1].document_series_key == "employment_letter"
    assert docs[1].document_version == 2
    assert docs[1].is_active is True
    assert docs[1].supersedes_document_id == docs[0].id
    assert docs[1].source_path == "/tmp/offer_v2.pdf"


def test_v2_upload_can_infer_doc_type_when_omitted(client, db_session, monkeypatch):
    check_id = client.post("/api/checks", json={"track": "data_room", "answers": {"stage": "data_room"}}).json()["id"]
    calls: list[tuple[str, str, str | None, bool]] = []

    def fake_resolve(file_path: str, mime_type: str, *, provided_doc_type=None, allow_ocr: bool = False):
        calls.append((file_path, mime_type, provided_doc_type, allow_ocr))
        return ResolvedDocumentType(doc_type="lease", confidence="high", source="filename")

    monkeypatch.setattr(extraction_mod, "resolve_document_type", fake_resolve)

    resp = client.post(
        f"/api/checks/{check_id}/documents",
        data={"source_path": "/tmp/sublease agreement.pdf"},
        files={"file": ("sublease agreement.pdf", b"lease-1", "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["doc_type"] == "lease"
    assert calls and calls[0][2] is None
    assert calls[0][3] is False

    db_session.expire_all()
    doc = db_session.get(DocumentRow, resp.json()["id"])
    assert doc.doc_type == "lease"
    assert doc.provenance["classification"]["source"] == "filename"
    assert doc.provenance["classification"]["doc_type"] == "lease"


def test_v2_upload_normalizes_user_doc_type_and_persists_classification_provenance(client, db_session):
    check_id = client.post("/api/checks", json={"track": "data_room", "answers": {"stage": "data_room"}}).json()["id"]

    resp = client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "1042-S", "source_path": "/tmp/1042S.pdf"},
        files={"file": ("1042S.pdf", b"tax-form", "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["doc_type"] == "1042s"

    db_session.expire_all()
    doc = db_session.get(DocumentRow, resp.json()["id"])
    assert doc.doc_type == "1042s"
    assert doc.provenance["classification"] == {
        "doc_type": "1042s",
        "source": "user",
        "confidence": "high",
        "provided_doc_type": "1042-S",
    }


def test_extract_persists_ocr_text_and_provenance(client, db_session, monkeypatch):
    import compliance_os.web.services.document_store as document_store

    check = CheckRow(track="stem_opt", status="uploaded", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()
    doc = DocumentRow(
        check_id=check.id,
        doc_type="i94",
        filename="i94.pdf",
        source_path="/tmp/i94.pdf",
        file_path="/tmp/i94.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    db_session.add(doc)
    db_session.commit()

    monkeypatch.setattr(
        document_store,
        "extract_pdf_text_with_provenance",
        lambda _: TextExtractionResult(
            text="Admission Number: 600626988A3\nClass of Admission: F1",
            engine="test_ocr",
            metadata={"page_count": 1},
        ),
    )
    monkeypatch.setattr(
        document_store,
        "extract_document",
        lambda doc_type, text: {
            "admission_number": {"value": "600626988A3", "confidence": 0.9},
            "class_of_admission": {"value": "F1", "confidence": 0.9},
        },
    )

    resp = client.post(f"/api/checks/{check.id}/extract")
    assert resp.status_code == 200

    db_session.expire_all()
    refreshed = db_session.get(DocumentRow, doc.id)
    assert refreshed.ocr_text.startswith("Admission Number")
    assert refreshed.ocr_engine == "test_ocr"
    assert refreshed.provenance["ocr"]["engine"] == "test_ocr"
    extracted = (
        db_session.query(ExtractedFieldRow)
        .filter(ExtractedFieldRow.document_id == doc.id, ExtractedFieldRow.field_name == "admission_number")
        .one()
    )
    assert "Admission Number" in extracted.raw_text


def test_different_doc_types_keep_independent_lineage(client, db_session):
    check_id = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "stem_opt"}}).json()["id"]

    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "i983", "source_path": "/tmp/i983.pdf"},
        files={"file": ("i983.pdf", b"i983", "application/pdf")},
    )
    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "employment_letter", "source_path": "/tmp/offer.pdf"},
        files={"file": ("offer.pdf", b"offer", "application/pdf")},
    )
    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "ead", "source_path": "/tmp/ead.jpg"},
        files={"file": ("ead.jpg", b"ead", "image/jpeg")},
    )

    db_session.expire_all()
    docs = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check_id)
        .order_by(DocumentRow.doc_type.asc(), DocumentRow.id.asc())
        .all()
    )

    assert [doc.document_family for doc in docs] == ["ead", "employment_letter", "i983"]
    assert [doc.document_series_key for doc in docs] == ["ead", "employment_letter", "i983"]
    assert all(doc.document_version == 1 for doc in docs)
    assert all(doc.is_active is True for doc in docs)
    assert all(doc.supersedes_document_id is None for doc in docs)


def test_same_doc_type_can_keep_independent_series_keys(client, db_session):
    check_id = client.post("/api/checks", json={"track": "data_room", "answers": {"stage": "data_room"}}).json()["id"]

    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "lease", "source_path": "/tmp/Complete_with_DocuSign_Standard_Lease_-_The_.pdf"},
        files={"file": ("Complete_with_DocuSign_Standard_Lease_-_The_.pdf", b"lease-1", "application/pdf")},
    )
    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "lease", "source_path": "/tmp/sublease agreement.pdf"},
        files={"file": ("sublease agreement.pdf", b"lease-2", "application/pdf")},
    )

    db_session.expire_all()
    docs = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check_id)
        .order_by(DocumentRow.filename.asc())
        .all()
    )

    assert len(docs) == 2
    assert {doc.document_family for doc in docs} == {"lease"}
    assert {doc.document_series_key for doc in docs} == {
        "lease:lease:complete-with-docusign-standard-lease-the",
        "lease:sublease:sublease-agreement",
    }
    assert all(doc.document_version == 1 for doc in docs)
    assert all(doc.is_active is True for doc in docs)
    assert all(doc.supersedes_document_id is None for doc in docs)


def test_same_i9_doc_type_can_keep_independent_series_keys(client, db_session):
    check_id = client.post("/api/checks", json={"track": "data_room", "answers": {"stage": "data_room"}}).json()["id"]

    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "i9", "source_path": "employment/VCV/I9.pdf"},
        files={"file": ("I9.pdf", b"i9-vcv", "application/pdf")},
    )
    client.post(
        f"/api/checks/{check_id}/documents",
        data={"doc_type": "i9", "source_path": "employment/Wolff & Li/wolff-li-capital-i-9-signed.pdf"},
        files={"file": ("wolff-li-capital-i-9-signed.pdf", b"i9-wolff", "application/pdf")},
    )

    db_session.expire_all()
    docs = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check_id)
        .order_by(DocumentRow.filename.asc())
        .all()
    )

    assert len(docs) == 2
    assert {doc.document_family for doc in docs} == {"i9"}
    assert {doc.document_series_key for doc in docs} == {"i9:vcv", "i9:wolff-li"}
    assert all(doc.document_version == 1 for doc in docs)
    assert all(doc.is_active is True for doc in docs)


def test_extraction_refines_paystub_series_key_by_employer_and_period_end(client, db_session, monkeypatch):
    import compliance_os.web.services.document_store as document_store

    check = CheckRow(track="data_room", status="uploaded", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    doc = DocumentRow(
        check_id=check.id,
        doc_type="paystub",
        filename="Paystub20240112.pdf",
        source_path="/tmp/Paystub20240112.pdf",
        file_path="/tmp/Paystub20240112.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="paystub-a",
        document_family="paystub",
        document_series_key="paystub",
    )
    db_session.add(doc)
    db_session.commit()

    monkeypatch.setattr(
        document_store,
        "extract_pdf_text_with_provenance",
        lambda path: TextExtractionResult(
            text="Pay Period End 01/15/2024 Pay Date 01/12/2024",
            engine="test_ocr",
            metadata={"page_count": 1},
        ),
    )
    monkeypatch.setattr(
        document_store,
        "extract_document",
        lambda doc_type, text: {
            "employer_name": {"value": "Tiger Cloud LLC", "confidence": 0.9},
            "pay_period_end": {"value": "2024-01-15", "confidence": 0.9},
        },
    )

    document_store.extract_into_document(doc, db_session)
    db_session.commit()
    db_session.expire_all()

    refreshed = db_session.get(DocumentRow, doc.id)
    assert refreshed.document_series_key == "paystub:tiger-cloud-llc:2024-01-15"
    assert refreshed.document_version == 1
    assert refreshed.is_active is True


def test_extraction_refines_i765_series_key_by_eligibility_category(client, db_session, monkeypatch):
    import compliance_os.web.services.document_store as document_store

    check = CheckRow(track="data_room", status="uploaded", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    stem = DocumentRow(
        check_id=check.id,
        doc_type="i765",
        filename="application-a.pdf",
        source_path="/tmp/application-a.pdf",
        file_path="/tmp/application-a.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="i765-a",
        document_family="i765",
        document_series_key="i765",
    )
    opt = DocumentRow(
        check_id=check.id,
        doc_type="i765",
        filename="application-b.pdf",
        source_path="/tmp/application-b.pdf",
        file_path="/tmp/application-b.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="i765-b",
        document_family="i765",
        document_series_key="i765",
    )
    db_session.add_all([stem, opt])
    db_session.commit()

    monkeypatch.setattr(
        document_store,
        "extract_pdf_text_with_provenance",
        lambda path: TextExtractionResult(
            text="Application For Employment Authorization Form I-765",
            engine="test_ocr",
            metadata={"page_count": 1},
        ),
    )

    current_doc = {"filename": ""}

    def fake_extract_dispatch(doc_type, text):
        return {
            "eligibility_category": {"value": "C03C" if current_doc["filename"] == "application-a.pdf" else "C03B", "confidence": 0.9},
            "applicant_name": {"value": "Chenyu Li", "confidence": 0.9},
        }

    monkeypatch.setattr(document_store, "extract_document", fake_extract_dispatch)

    current_doc["filename"] = "application-a.pdf"
    document_store.extract_into_document(stem, db_session)
    current_doc["filename"] = "application-b.pdf"
    document_store.extract_into_document(opt, db_session)
    db_session.commit()
    db_session.expire_all()

    refreshed = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check.id)
        .order_by(DocumentRow.filename.asc())
        .all()
    )
    assert refreshed[0].document_series_key == "i765:c03c"
    assert refreshed[1].document_series_key == "i765:c03b"
    assert all(doc.document_version == 1 for doc in refreshed)
    assert all(doc.is_active is True for doc in refreshed)


def test_extraction_cross_checks_i9_first_day_with_everify(client, db_session, monkeypatch):
    import compliance_os.web.services.document_store as document_store

    check = CheckRow(track="data_room", status="uploaded", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    i9_doc = DocumentRow(
        check_id=check.id,
        doc_type="i9",
        filename="wolff-li-capital-i-9-signed.pdf",
        source_path="employment/Wolff & Li/wolff-li-capital-i-9-signed.pdf",
        file_path="/tmp/wolff-li-capital-i-9-signed.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="i9-wolff",
        document_family="i9",
        document_series_key="i9:wolff-li",
    )
    everify_doc = DocumentRow(
        check_id=check.id,
        doc_type="e_verify_case",
        filename="everify.pdf",
        source_path="employment/Wolff & Li/E-Verify Case Processing_ View_Print Details.pdf",
        file_path="/tmp/everify.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="everify-wolff",
        document_family="e_verify_case",
        document_series_key="e_verify_case",
    )
    db_session.add_all([i9_doc, everify_doc])
    db_session.commit()

    monkeypatch.setattr(
        document_store,
        "extract_pdf_text_with_provenance",
        lambda path: TextExtractionResult(
            text=f"Mock OCR for {path}",
            engine="test_ocr",
            metadata={"page_count": 1},
        ),
    )

    def fake_extract_dispatch(doc_type, text):
        if doc_type == "i9":
            return {
                "employee_name": {"value": "Alex Zhang", "confidence": 0.9},
                "employee_first_day_of_employment": {"value": "2026-03-17", "confidence": 0.9},
            }
        if doc_type == "e_verify_case":
            return {
                "employee_name": {"value": "Alex Zhang", "confidence": 0.9},
                "employee_first_day_of_employment": {"value": "2025-03-17", "confidence": 0.9},
                "case_number": {"value": "2025079225618BC", "confidence": 0.9},
            }
        return {}

    monkeypatch.setattr(document_store, "extract_document", fake_extract_dispatch)

    document_store.extract_into_document(i9_doc, db_session)
    document_store.extract_into_document(everify_doc, db_session)
    db_session.commit()
    db_session.expire_all()

    corrected_field = (
        db_session.query(ExtractedFieldRow)
        .filter(
            ExtractedFieldRow.document_id == i9_doc.id,
            ExtractedFieldRow.field_name == "employee_first_day_of_employment",
        )
        .one()
    )
    assert corrected_field.field_value == "2025-03-17"
    assert corrected_field.confidence == 0.75
    assert "Cross-checked against related E-Verify" in (corrected_field.raw_text or "")

    refreshed_i9 = db_session.get(DocumentRow, i9_doc.id)
    cross_check = refreshed_i9.provenance["structured_extraction"]["cross_checks"]["employee_first_day_of_employment"]
    assert cross_check["status"] == "corrected_year_typo"
    assert cross_check["original_value"] == "2026-03-17"
    assert cross_check["resolved_value"] == "2025-03-17"


def test_extraction_refines_1042s_series_key_by_tax_year(client, db_session, monkeypatch):
    import compliance_os.web.services.document_store as document_store

    check = CheckRow(track="data_room", status="uploaded", answers={"stage": "data_room"})
    db_session.add(check)
    db_session.flush()

    doc_2024 = DocumentRow(
        check_id=check.id,
        doc_type="1042s",
        filename="statement-a.pdf",
        source_path="/tmp/statement-a.pdf",
        file_path="/tmp/statement-a.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="a",
        document_family="1042s",
        document_series_key="1042s",
    )
    doc_2025 = DocumentRow(
        check_id=check.id,
        doc_type="1042s",
        filename="statement-b.pdf",
        source_path="/tmp/statement-b.pdf",
        file_path="/tmp/statement-b.pdf",
        file_size=100,
        mime_type="application/pdf",
        content_hash="b",
        document_family="1042s",
        document_series_key="1042s",
    )
    db_session.add_all([doc_2024, doc_2025])
    db_session.commit()

    monkeypatch.setattr(
        document_store,
        "extract_pdf_text_with_provenance",
        lambda path: TextExtractionResult(
            text="Form 1042-S recipient's date of birth 320106199809180413",
            engine="test_ocr",
            metadata={"page_count": 1},
        ),
    )

    current_doc = {"filename": ""}

    def fake_extract_dispatch(doc_type, text):
        return {
            "tax_year": {"value": "2024" if current_doc["filename"] == "statement-a.pdf" else "2025", "confidence": 0.9},
            "recipient_account_number": {"value": "7689-2619", "confidence": 0.9},
        }

    monkeypatch.setattr(document_store, "extract_document", fake_extract_dispatch)

    current_doc["filename"] = "statement-a.pdf"
    document_store.extract_into_document(doc_2024, db_session)
    current_doc["filename"] = "statement-b.pdf"
    document_store.extract_into_document(doc_2025, db_session)
    db_session.commit()
    db_session.expire_all()

    refreshed = (
        db_session.query(DocumentRow)
        .filter(DocumentRow.check_id == check.id)
        .order_by(DocumentRow.filename.asc())
        .all()
    )
    assert refreshed[0].document_series_key == "1042s:2024:7689-2619"
    assert refreshed[1].document_series_key == "1042s:2025:7689-2619"
    assert all(doc.document_version == 1 for doc in refreshed)
    assert all(doc.is_active is True for doc in refreshed)


def test_retrieval_context_endpoint_returns_active_and_prior_versions(client, db_session):
    check = CheckRow(track="stem_opt", status="reviewed", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    old_doc = DocumentRow(
        check_id=check.id,
        doc_type="employment_letter",
        document_family="employment_letter",
        document_version=1,
        is_active=False,
        filename="offer_old.pdf",
        source_path="/tmp/offer_old.pdf",
        file_path="/tmp/offer_old.pdf",
        file_size=100,
        mime_type="application/pdf",
        ocr_text="Old employer letter for Tiger Cloud LLC",
        ocr_engine="test_ocr",
        uploaded_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    new_doc = DocumentRow(
        check_id=check.id,
        doc_type="employment_letter",
        document_family="employment_letter",
        document_version=2,
        is_active=True,
        filename="offer_new.pdf",
        source_path="/tmp/offer_new.pdf",
        file_path="/tmp/offer_new.pdf",
        file_size=100,
        mime_type="application/pdf",
        ocr_text="Current employer letter for CliniPulse LLC and start date 2025-02-20",
        ocr_engine="test_ocr",
        uploaded_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([old_doc, new_doc])
    db_session.flush()
    db_session.add(ExtractedFieldRow(document_id=new_doc.id, field_name="employer_name", field_value="CliniPulse LLC", confidence=0.9))
    db_session.commit()

    resp = client.get(f"/api/checks/{check.id}/retrieval-context", params={"query": "current employer start date"})
    assert resp.status_code == 200
    body = resp.json()
    family = next(item for item in body["families"] if item["document_family"] == "employment_letter")
    assert family["active_document"]["filename"] == "offer_new.pdf"
    assert family["document_series_key"] == "employment_letter"
    assert family["active_document"]["document_version"] == 2
    assert len(family["prior_versions"]) == 1
    assert body["retrieved_documents"][0]["filename"] == "offer_new.pdf"


def test_extractions_endpoint_returns_versioned_documents(client, db_session):
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    doc = DocumentRow(
        check_id=check.id,
        doc_type="i94",
        document_family="i94",
        document_version=2,
        is_active=True,
        filename="i94-latest.pdf",
        source_path="/tmp/i94-latest.pdf",
        file_path="/tmp/i94-latest.pdf",
        file_size=100,
        mime_type="application/pdf",
        ocr_engine="test_ocr",
        provenance={"ocr": {"engine": "test_ocr"}},
    )
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        ExtractedFieldRow(
            document_id=doc.id,
            field_name="class_of_admission",
            field_value="F1",
            confidence=0.9,
            raw_text="Class of Admission: F1",
        )
    )
    db_session.commit()

    resp = client.get(f"/api/checks/{check.id}/extractions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["document_family"] == "i94"
    assert body[0]["document_series_key"] == "i94"
    assert body[0]["document_version"] == 2
    assert body[0]["source_path"] == "/tmp/i94-latest.pdf"
    assert body[0]["ocr_engine"] == "test_ocr"
    assert body[0]["provenance"]["ocr"]["engine"] == "test_ocr"
    assert body[0]["extracted_fields"][0]["raw_text"] == "Class of Admission: F1"


def test_snapshot_includes_versioned_document_extractions(client, db_session):
    check = CheckRow(track="stem_opt", status="reviewed", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    doc = DocumentRow(
        check_id=check.id,
        doc_type="employment_letter",
        document_family="employment_letter",
        document_version=3,
        is_active=True,
        filename="offer-current.pdf",
        source_path="/tmp/offer-current.pdf",
        file_path="/tmp/offer-current.pdf",
        file_size=100,
        mime_type="application/pdf",
        ocr_engine="test_ocr",
        provenance={"ocr": {"engine": "test_ocr"}},
    )
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        ExtractedFieldRow(
            document_id=doc.id,
            field_name="employer_name",
            field_value="CliniPulse LLC",
            confidence=0.9,
            raw_text="Employer: CliniPulse LLC",
        )
    )
    db_session.commit()

    resp = client.get(f"/api/checks/{check.id}/snapshot")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_extractions"][0]["document_family"] == "employment_letter"
    assert body["document_extractions"][0]["document_series_key"] == "employment_letter"
    assert body["document_extractions"][0]["document_version"] == 3
    assert body["document_extractions"][0]["is_active"] is True
    assert body["document_extractions"][0]["provenance"]["ocr"]["engine"] == "test_ocr"
    assert body["document_extractions"][0]["extracted_fields"][0]["raw_text"] == "Employer: CliniPulse LLC"
