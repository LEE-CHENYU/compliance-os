"""Tests for the public Form 8843 generation API."""

from __future__ import annotations

import compliance_os.web.routers.form8843 as form8843_mod
from compliance_os.web.models import database


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

    pdf_response = client.get(body["pdf_url"])
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content[:4] == b"%PDF"

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
        assert order.result_data["pdf_path"]
        assert session.query(EmailSequenceRow).filter(EmailSequenceRow.user_id == user.id).count() == 1
    finally:
        session.close()
