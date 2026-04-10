"""Tests for marketplace database models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from compliance_os.web.models.database import create_engine_and_tables


def test_marketplace_tables_created(tmp_path):
    engine = create_engine_and_tables(str(tmp_path / "marketplace.db"))

    tables = set(inspect(engine).get_table_names())

    assert "mp_users" in tables
    assert "mp_products" in tables
    assert "mp_orders" in tables
    assert "mp_email_sequences" in tables


def test_create_marketplace_user_and_order(tmp_path):
    engine = create_engine_and_tables(str(tmp_path / "marketplace.db"))

    from compliance_os.web.models.marketplace import (
        EmailSequenceRow,
        MarketplaceUserRow,
        OrderRow,
        ProductRow,
    )

    with Session(engine) as session:
        user = MarketplaceUserRow(
            email="test@example.com",
            full_name="Test User",
            source="form_8843",
        )
        product = ProductRow(
            sku="form_8843_free",
            name="Form 8843 (Free)",
            description="Free Form 8843 generator",
            price_cents=0,
            tier="tier_0",
            requires_attorney=False,
            requires_questionnaire=False,
            active=True,
        )
        session.add_all([user, product])
        session.flush()

        order = OrderRow(
            user_id=user.id,
            product_sku=product.sku,
            status="completed",
            amount_cents=0,
            intake_data={"visa_type": "F-1"},
            result_data={"pdf_path": "/tmp/form_8843.pdf"},
            completed_at=datetime.now(timezone.utc),
        )
        sequence = EmailSequenceRow(
            user_id=user.id,
            sequence_name="form_8843_welcome",
            current_step=0,
            completed=False,
        )
        session.add_all([order, sequence])
        session.commit()

        assert user.id is not None
        assert order.id is not None
        assert user.orders[0].id == order.id
        assert user.email_sequences[0].sequence_name == "form_8843_welcome"
