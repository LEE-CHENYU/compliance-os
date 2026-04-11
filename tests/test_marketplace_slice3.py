"""Tests for Slice 3 marketplace product flows."""

from __future__ import annotations

from compliance_os.web.models import database
from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow


def _auth_headers(client, email: str) -> dict[str, str]:
    response = client.post("/api/auth/signup", json={"email": email, "password": "secure123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _create_order(client, headers: dict[str, str], sku: str) -> str:
    response = client.post(
        "/api/marketplace/orders",
        headers=headers,
        json={"sku": sku},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["product_sku"] == sku
    return body["order_id"]


def _disable_marketplace_delivery_email(monkeypatch) -> None:
    import compliance_os.web.routers.marketplace as marketplace_mod

    monkeypatch.setattr(
        marketplace_mod,
        "send_marketplace_delivery_email",
        lambda *args, **kwargs: {"status": "skipped"},
    )


def _seed_extracted_document(
    *,
    email: str,
    doc_type: str,
    filename: str,
    fields: dict[str, str],
    tmp_path,
) -> None:
    session = database._SessionLocal()
    try:
        user = session.query(UserRow).filter(UserRow.email == email).one()
        check = CheckRow(track="stem_opt", status="saved", user_id=user.id, answers={})
        session.add(check)
        session.flush()

        file_path = tmp_path / filename
        file_path.write_text("seed", encoding="utf-8")
        document = DocumentRow(
            check_id=check.id,
            doc_type=doc_type,
            filename=filename,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type="text/plain",
            is_active=True,
        )
        session.add(document)
        session.flush()

        for field_name, field_value in fields.items():
            session.add(
                ExtractedFieldRow(
                    document_id=document.id,
                    field_name=field_name,
                    field_value=str(field_value),
                    confidence=0.99,
                    raw_text=str(field_value),
                )
            )
        session.commit()
    finally:
        session.close()


def test_h1b_doc_check_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.h1b_doc_check as h1b_mod

    monkeypatch.setattr(h1b_mod, "H1B_DOC_CHECK_DIR", tmp_path / "h1b")
    _disable_marketplace_delivery_email(monkeypatch)

    headers = _auth_headers(client, "h1b-orders@example.com")
    order_id = _create_order(client, headers, "h1b_doc_check")

    intake_response = client.post(
        f"/api/marketplace/orders/{order_id}/intake",
        headers=headers,
        files=[
            (
                "h1b_registration_file",
                (
                    "registration.txt",
                    b"Registration Number: H1BR123456\nEmployer Name: Acme Labs Inc.\nAuthorized Individual Name: Jane Founder\nAuthorized Individual Title: CEO",
                    "text/plain",
                ),
            ),
            (
                "h1b_g28_file",
                (
                    "g28.txt",
                    b"Representative Name: Xinzi Chen\nLaw Firm Name: Guardian Legal\nClient Entity Name: Different Entity LLC",
                    "text/plain",
                ),
            ),
            (
                "h1b_filing_invoice_file",
                (
                    "invoice.txt",
                    b"Invoice Number: H1B-2026-01\nPetitioner Name: Acme Labs Inc.\nBeneficiary Name: Raj Patel\nTotal Due Amount: 460.00",
                    "text/plain",
                ),
            ),
            (
                "h1b_filing_fee_receipt_file",
                (
                    "receipt.txt",
                    b"Transaction ID: TX-7788\nCardholder Name: Raj Patel\nAmount: 460.00\nResponse Message: APPROVAL",
                    "text/plain",
                ),
            ),
            (
                "h1b_status_summary_file",
                (
                    "status.txt",
                    b"Status Title: H-1B Status\nPetition Filing Window End Date: 2026-03-31\nEmployment Start Date: 2026-10-01",
                    "text/plain",
                ),
            ),
        ],
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["status"] == "intake_complete"

    process_response = client.post(
        f"/api/marketplace/orders/{order_id}/process",
        headers=headers,
    )
    assert process_response.status_code == 200
    assert process_response.json()["status"] == "completed"

    result_response = client.get(
        f"/api/marketplace/orders/{order_id}/result",
        headers=headers,
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["finding_count"] >= 1
    assert any("entity" in finding["title"].lower() for finding in result["findings"])
    assert result["artifacts"]

    report_response = client.get(result["artifacts"][0]["url"], headers=headers)
    assert report_response.status_code == 200
    assert report_response.headers["content-type"] == "application/pdf"
    assert report_response.content[:4] == b"%PDF"


def test_fbar_check_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.fbar_check as fbar_mod

    monkeypatch.setattr(fbar_mod, "FBAR_CHECK_DIR", tmp_path / "fbar")
    _disable_marketplace_delivery_email(monkeypatch)

    headers = _auth_headers(client, "fbar-orders@example.com")
    order_id = _create_order(client, headers, "fbar_check")

    intake_response = client.post(
        f"/api/marketplace/orders/{order_id}/intake",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "tax_year": 2025,
            "owner_name": "Wei Liu",
            "accounts": [
                {
                    "institution_name": "HSBC Hong Kong",
                    "country": "Hong Kong",
                    "account_type": "Checking",
                    "max_balance_usd": 7000,
                    "account_number_last4": "1122",
                },
                {
                    "institution_name": "ICBC Beijing",
                    "country": "China",
                    "account_type": "Savings",
                    "max_balance_usd": 4500,
                    "account_number_last4": "7788",
                },
            ],
        },
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["status"] == "intake_complete"

    process_response = client.post(
        f"/api/marketplace/orders/{order_id}/process",
        headers=headers,
    )
    assert process_response.status_code == 200

    result_response = client.get(
        f"/api/marketplace/orders/{order_id}/result",
        headers=headers,
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["requires_fbar"] is True
    assert result["aggregate_max_balance_usd"] == 11500
    assert "FinCEN" in result["summary"]
    assert result["artifacts"]


def test_83b_election_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.election_83b as election_mod

    monkeypatch.setattr(election_mod, "ELECTION_83B_DIR", tmp_path / "83b")
    _disable_marketplace_delivery_email(monkeypatch)

    headers = _auth_headers(client, "83b-orders@example.com")
    order_id = _create_order(client, headers, "election_83b")

    intake_response = client.post(
        f"/api/marketplace/orders/{order_id}/intake",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "taxpayer_name": "Jessica Chen",
            "taxpayer_address": "123 Startup Way, San Francisco, CA 94107",
            "company_name": "CliniPulse, Inc.",
            "property_description": "Restricted common stock",
            "grant_date": "2026-04-01",
            "share_count": 10000,
            "fair_market_value_per_share": 0.02,
            "exercise_price_per_share": 0.01,
            "vesting_schedule": "25% after 12 months, then monthly over 36 months",
        },
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["status"] == "intake_complete"

    process_response = client.post(
        f"/api/marketplace/orders/{order_id}/process",
        headers=headers,
    )
    assert process_response.status_code == 200
    process_body = process_response.json()
    assert process_body["status"] == "completed"
    assert process_body["mailing_status"] == "needs_signature"
    assert process_body["filing_deadline"] == "2026-05-01"

    result_response = client.get(
        f"/api/marketplace/orders/{order_id}/result",
        headers=headers,
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["filing_deadline"] == "2026-05-01"
    assert any("certified mail" in step.lower() for step in result["next_steps"])
    assert len(result["artifacts"]) == 2

    mark_mailed_response = client.post(
        f"/api/marketplace/orders/{order_id}/mark-mailed",
        headers=headers,
        json={"tracking_number": "9407 1000 0000 0000 1234 56"},
    )
    assert mark_mailed_response.status_code == 200
    assert mark_mailed_response.json()["mailing_status"] == "mailed"

    from compliance_os.web.models.marketplace import EmailSequenceRow

    session = database._SessionLocal()
    try:
        sequences = (
            session.query(EmailSequenceRow)
            .filter(EmailSequenceRow.user_id == mark_mailed_response.json()["user_id"])
            .all()
        )
        assert any(sequence.sequence_name.startswith("election_83b_deadline:") for sequence in sequences)
    finally:
        session.close()


def test_student_tax_1040nr_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.student_tax_check as student_tax_mod

    monkeypatch.setattr(student_tax_mod, "STUDENT_TAX_DIR", tmp_path / "student-tax")
    _disable_marketplace_delivery_email(monkeypatch)

    headers = _auth_headers(client, "student-tax-orders@example.com")
    order_id = _create_order(client, headers, "student_tax_1040nr")

    intake_response = client.post(
        f"/api/marketplace/orders/{order_id}/intake",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "tax_year": 2025,
            "full_name": "Jessica Chen",
            "visa_type": "F-1",
            "school_name": "Columbia University",
            "country_citizenship": "China",
            "arrival_date": "2023-08-18",
            "days_present_current": 320,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
            "wage_income_usd": 24000,
            "federal_withholding_usd": 1800,
            "state_withholding_usd": 450,
            "claim_treaty_benefit": True,
            "treaty_country": "China",
            "treaty_article": "Article 20(c)",
        },
    )
    assert intake_response.status_code == 200
    assert intake_response.json()["status"] == "intake_complete"

    process_response = client.post(
        f"/api/marketplace/orders/{order_id}/process",
        headers=headers,
    )
    assert process_response.status_code == 200
    process_body = process_response.json()
    assert process_body["status"] == "completed"
    assert process_body["filing_deadline"] == "2026-04-15"

    result_response = client.get(
        f"/api/marketplace/orders/{order_id}/result",
        headers=headers,
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["filing_deadline"] == "2026-04-15"
    assert result["total_income_usd"] == 24000
    assert len(result["artifacts"]) >= 2
    assert any("1040-NR" in artifact["label"] for artifact in result["artifacts"])
    assert result["notification_statuses"]["delivery_email"]["status"] == "skipped"


def test_student_tax_prefill_pulls_extracted_fields(client, monkeypatch, tmp_path):
    _disable_marketplace_delivery_email(monkeypatch)

    email = "student-tax-prefill@example.com"
    headers = _auth_headers(client, email)
    _seed_extracted_document(
        email=email,
        doc_type="passport",
        filename="passport.txt",
        fields={
            "full_name": "Jessica Chen",
            "country_of_issue": "China",
        },
        tmp_path=tmp_path,
    )
    _seed_extracted_document(
        email=email,
        doc_type="i20",
        filename="i20.txt",
        fields={
            "student_name": "Jessica Chen",
            "school_name": "Columbia University",
        },
        tmp_path=tmp_path,
    )
    _seed_extracted_document(
        email=email,
        doc_type="i94",
        filename="i94.txt",
        fields={
            "most_recent_entry_date": "2023-08-18",
            "class_of_admission": "F-1",
        },
        tmp_path=tmp_path,
    )
    _seed_extracted_document(
        email=email,
        doc_type="w2",
        filename="w2.txt",
        fields={
            "tax_year": "2025",
            "wages_tips_other_compensation": "24000",
            "federal_income_tax_withheld": "1800",
        },
        tmp_path=tmp_path,
    )

    order_id = _create_order(client, headers, "student_tax_1040nr")
    response = client.post(
        f"/api/marketplace/orders/{order_id}/pull-extracted-info",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["prefill"]["coverage"] == "partial"
    assert body["order"]["status"] == "draft"
    preview = body["order"]["intake_preview"]
    assert preview["full_name"] == "Jessica Chen"
    assert preview["school_name"] == "Columbia University"
    assert preview["tax_year"] == 2025
    assert len(body["prefill"]["source_documents"]) >= 3


def test_h1b_prefill_allows_processing_without_manual_upload(client, monkeypatch, tmp_path):
    import compliance_os.web.services.h1b_doc_check as h1b_mod

    monkeypatch.setattr(h1b_mod, "H1B_DOC_CHECK_DIR", tmp_path / "h1b")
    _disable_marketplace_delivery_email(monkeypatch)

    email = "h1b-prefill@example.com"
    headers = _auth_headers(client, email)
    _seed_extracted_document(
        email=email,
        doc_type="h1b_registration",
        filename="registration.txt",
        fields={
            "registration_number": "ABC123456789",
            "employer_name": "Acme Labs Inc.",
            "authorized_individual_name": "Jane Founder",
            "authorized_individual_title": "CEO",
        },
        tmp_path=tmp_path,
    )
    _seed_extracted_document(
        email=email,
        doc_type="h1b_g28",
        filename="g28.txt",
        fields={
            "representative_name": "Xinzi Chen",
            "client_entity_name": "Different Entity LLC",
        },
        tmp_path=tmp_path,
    )

    order_id = _create_order(client, headers, "h1b_doc_check")
    prefill_response = client.post(
        f"/api/marketplace/orders/{order_id}/pull-extracted-info",
        headers=headers,
    )
    assert prefill_response.status_code == 200
    assert prefill_response.json()["order"]["status"] == "intake_complete"

    process_response = client.post(
        f"/api/marketplace/orders/{order_id}/process",
        headers=headers,
    )
    assert process_response.status_code == 200
    result = process_response.json()["result"]
    assert result["document_summary"]
    assert any("entity" in finding["title"].lower() for finding in result["findings"])
