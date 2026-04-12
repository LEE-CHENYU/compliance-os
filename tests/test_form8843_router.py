"""Tests for the public Form 8843 generation API."""

from __future__ import annotations

import compliance_os.web.routers.form8843 as form8843_mod
from compliance_os.web.models import database


def _auth_token(client, email: str) -> str:
    response = client.post("/api/auth/register", json={"email": email, "password": "secure123"})
    assert response.status_code == 200
    return response.json()["token"]


def test_form8843_generate_endpoint(client, monkeypatch, tmp_path):
    monkeypatch.setattr(form8843_mod, "FORM_8843_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        form8843_mod,
        "send_form_8843_welcome",
        lambda *args, **kwargs: {"status": "skipped"},
    )

    response = client.post(
        "/api/form8843/generate",
        json={
            "email": "test@example.com",
            "full_name": "Test User",
            "visa_type": "F-1",
            "school_name": "Columbia University",
            "country_citizenship": "China",
            "country_passport": "China",
            "passport_number": "E12345678",
            "days_present_current": 340,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["order_id"]
    assert body["user_id"]
    assert body["pdf_url"].endswith(f"/api/form8843/orders/{body['order_id']}/pdf")
    assert body["mailing_status"] == "needs_signature"
    assert body["filing_deadline"] == "2026-06-15"
    assert "Austin, TX 73301-0215" in body["filing_instructions"]["address_block"]

    pdf_response = client.get(body["pdf_url"])
    assert pdf_response.status_code == 401

    token = _auth_token(client, "test@example.com")
    pdf_response = client.get(body["pdf_url"], headers={"Authorization": f"Bearer {token}"})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content[:4] == b"%PDF"

    wrong_token = _auth_token(client, "other@example.com")
    wrong_pdf_response = client.get(body["pdf_url"], headers={"Authorization": f"Bearer {wrong_token}"})
    assert wrong_pdf_response.status_code == 403
    assert "same email used for this form" in wrong_pdf_response.json()["detail"]

    order_response = client.get(f"/api/form8843/orders/{body['order_id']}")
    assert order_response.status_code == 200
    assert order_response.json()["mailing_status"] == "needs_signature"

    mailing_kit_response = client.get(f"/api/form8843/orders/{body['order_id']}/mailing-kit")
    assert mailing_kit_response.status_code == 200
    assert "Austin, TX 73301-0215" in mailing_kit_response.json()["address_block"]

    mark_mailed_response = client.post(
        f"/api/form8843/orders/{body['order_id']}/mark-mailed",
        json={"tracking_number": "9407 1000 0000 0000 0000 00"},
    )
    assert mark_mailed_response.status_code == 200
    assert mark_mailed_response.json()["mailing_status"] == "mailed"
    assert mark_mailed_response.json()["tracking_number"] == "9407 1000 0000 0000 0000 00"

    from compliance_os.web.models.marketplace import EmailSequenceRow, MarketplaceUserRow, OrderRow

    session = database._SessionLocal()
    try:
        user = session.get(MarketplaceUserRow, body["user_id"])
        order = session.get(OrderRow, body["order_id"])
        assert user is not None
        assert user.email == "test@example.com"
        assert order is not None
        assert order.product_sku == "form_8843_free"
        assert order.status == "completed"
        assert order.delivery_method == "user_mail"
        assert order.filing_deadline.isoformat() == "2026-06-15"
        assert order.mailing_status == "mailed"
        assert order.tracking_number == "9407 1000 0000 0000 0000 00"
        assert order.result_data["pdf_path"]
        sequences = session.query(EmailSequenceRow).filter(EmailSequenceRow.user_id == user.id).all()
        assert len(sequences) == 3
        by_name = {sequence.sequence_name: sequence for sequence in sequences}
        assert f"form_8843_welcome:{order.id}" in by_name
        assert by_name[f"form_8843_mail_reminder:{order.id}"].completed is True
        assert by_name[f"form_8843_deadline_reminder:{order.id}"].completed is True
    finally:
        session.close()


def test_form8843_generate_without_email_claims_on_authenticated_download(client, monkeypatch, tmp_path):
    monkeypatch.setattr(form8843_mod, "FORM_8843_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        form8843_mod,
        "send_form_8843_welcome",
        lambda *args, **kwargs: {"status": "skipped"},
    )

    response = client.post(
        "/api/form8843/generate",
        json={
            "full_name": "Guest User",
            "visa_type": "F-1",
            "school_name": "Columbia University",
            "country_citizenship": "China",
            "country_passport": "China",
            "passport_number": "E12345678",
            "days_present_current": 340,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["order_id"]
    assert body.get("user_id") is None
    assert body["email_status"] == "claim_required"

    pdf_response = client.get(body["pdf_url"])
    assert pdf_response.status_code == 401

    token = _auth_token(client, "claimed@example.com")
    claimed_pdf_response = client.get(body["pdf_url"], headers={"Authorization": f"Bearer {token}"})
    assert claimed_pdf_response.status_code == 200
    assert claimed_pdf_response.headers["content-type"] == "application/pdf"
    assert claimed_pdf_response.content[:4] == b"%PDF"

    from compliance_os.web.models.marketplace import EmailSequenceRow, MarketplaceUserRow, OrderRow

    session = database._SessionLocal()
    try:
        order = session.get(OrderRow, body["order_id"])
        assert order is not None
        claimed_user = session.get(MarketplaceUserRow, order.user_id)
        assert claimed_user is not None
        assert claimed_user.email == "claimed@example.com"
        sequences = session.query(EmailSequenceRow).filter(EmailSequenceRow.user_id == claimed_user.id).all()
        assert len(sequences) == 3
    finally:
        session.close()
