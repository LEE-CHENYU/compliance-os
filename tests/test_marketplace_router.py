"""Tests for marketplace catalog endpoints."""

from __future__ import annotations

import compliance_os.web.routers.form8843 as form8843_mod
from compliance_os.web.models import database


def test_marketplace_products_endpoint(client):
    response = client.get("/api/marketplace/products")
    assert response.status_code == 200
    body = response.json()

    assert "products" in body
    skus = {product["sku"] for product in body["products"]}
    assert "form_8843_free" in skus
    assert "student_tax_1040nr" in skus
    assert "form_8843_mailing_service" not in skus

    session = database._SessionLocal()
    try:
        from compliance_os.web.models.marketplace import ProductRow

        rows = session.query(ProductRow).all()
        assert any(row.sku == "form_8843_free" for row in rows)
        assert any(row.sku == "form_8843_mailing_service" for row in rows)
    finally:
        session.close()


def test_marketplace_product_detail_endpoint(client):
    response = client.get("/api/marketplace/products/form_8843_free")
    assert response.status_code == 200
    body = response.json()

    assert body["sku"] == "form_8843_free"
    assert body["price_cents"] == 0
    assert body["path"] == "/form-8843"
    assert body["highlights"]


def test_marketplace_product_detail_can_include_inactive(client):
    response = client.get("/api/marketplace/products/form_8843_mailing_service?include_inactive=true")
    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "form_8843_mailing_service"
    assert body["active"] is False


def test_marketplace_orders_endpoints(client, monkeypatch, tmp_path):
    monkeypatch.setattr(form8843_mod, "FORM_8843_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        form8843_mod,
        "send_form_8843_welcome",
        lambda *args, **kwargs: {"status": "skipped"},
    )

    signup = client.post("/api/auth/signup", json={"email": "orders@example.com", "password": "secure123"})
    assert signup.status_code == 200
    token = signup.json()["token"]

    generate = client.post(
        "/api/form8843/generate",
        json={
            "email": "orders@example.com",
            "full_name": "Orders Example",
            "visa_type": "F-1",
            "school_name": "Columbia University",
            "country_citizenship": "China",
            "days_present_current": 340,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
        },
    )
    assert generate.status_code == 200
    order_id = generate.json()["order_id"]

    list_response = client.get(
        "/api/marketplace/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["order_id"] == order_id
    assert orders[0]["product"]["sku"] == "form_8843_free"
    assert orders[0]["product"]["path"] == "/form-8843"
    assert orders[0]["mailing_status"] == "needs_signature"

    detail_response = client.get(
        f"/api/marketplace/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["order_id"] == order_id
    assert detail["pdf_url"].endswith(f"/api/form8843/orders/{order_id}/pdf")
    assert detail["filing_instructions"]["mail_required"] is True


def test_marketplace_orders_require_auth(client):
    response = client.get("/api/marketplace/orders")
    assert response.status_code == 401
