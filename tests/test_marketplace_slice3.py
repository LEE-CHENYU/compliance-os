"""Tests for Slice 3 marketplace product flows."""

from __future__ import annotations

from compliance_os.web.models import database


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


def test_h1b_doc_check_flow(client, monkeypatch, tmp_path):
    import compliance_os.web.services.h1b_doc_check as h1b_mod

    monkeypatch.setattr(h1b_mod, "H1B_DOC_CHECK_DIR", tmp_path / "h1b")

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
