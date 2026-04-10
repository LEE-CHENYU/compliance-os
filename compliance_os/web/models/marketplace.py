"""Marketplace-related database models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from compliance_os.web.models.tables_v2 import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MarketplaceUserRow(Base):
    __tablename__ = "mp_users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    source = Column(String, default="direct", nullable=False)
    locale = Column(String, default="en", nullable=False)
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    questionnaire_responses = relationship(
        "QuestionnaireResponseRow",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    orders = relationship("OrderRow", back_populates="user", cascade="all, delete-orphan")
    agreements = relationship(
        "LimitedScopeAgreementRow",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_sequences = relationship(
        "EmailSequenceRow",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ProductRow(Base):
    __tablename__ = "mp_products"

    sku = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    tier = Column(String, nullable=False)
    requires_attorney = Column(Boolean, default=False, nullable=False)
    requires_questionnaire = Column(Boolean, default=False, nullable=False)
    stripe_price_id = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now)

    questionnaire_configs = relationship(
        "QuestionnaireConfigRow",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    questionnaire_responses = relationship(
        "QuestionnaireResponseRow",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    orders = relationship("OrderRow", back_populates="product", cascade="all, delete-orphan")


class QuestionnaireConfigRow(Base):
    __tablename__ = "mp_questionnaire_configs"

    service_sku = Column(String, ForeignKey("mp_products.sku"), primary_key=True)
    config_yaml = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    product = relationship("ProductRow", back_populates="questionnaire_configs")


class QuestionnaireResponseRow(Base):
    __tablename__ = "mp_questionnaire_responses"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("mp_users.id"), nullable=False)
    service_sku = Column(String, ForeignKey("mp_products.sku"), nullable=False)
    responses = Column(JSON, nullable=False, default=list)
    recommendation = Column(String, nullable=True)
    user_choice = Column(String, nullable=True)
    override = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)

    user = relationship("MarketplaceUserRow", back_populates="questionnaire_responses")
    product = relationship("ProductRow", back_populates="questionnaire_responses")


class OrderRow(Base):
    __tablename__ = "mp_orders"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("mp_users.id"), nullable=False)
    product_sku = Column(String, ForeignKey("mp_products.sku"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    stripe_session_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    intake_data = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("MarketplaceUserRow", back_populates="orders")
    product = relationship("ProductRow", back_populates="orders")
    agreements = relationship(
        "LimitedScopeAgreementRow",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    attorney_assignments = relationship(
        "AttorneyAssignmentRow",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class LimitedScopeAgreementRow(Base):
    __tablename__ = "mp_limited_scope_agreements"

    id = Column(String, primary_key=True, default=_uuid)
    order_id = Column(String, ForeignKey("mp_orders.id"), nullable=False)
    user_id = Column(String, ForeignKey("mp_users.id"), nullable=False)
    attorney_id = Column(String, ForeignKey("mp_attorneys.id"), nullable=True)
    agreement_text = Column(Text, nullable=False)
    user_signature = Column(String, nullable=False)
    signed_at = Column(DateTime, default=_now)
    user_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    order = relationship("OrderRow", back_populates="agreements")
    user = relationship("MarketplaceUserRow", back_populates="agreements")
    attorney = relationship("AttorneyRow", back_populates="agreements")


class AttorneyRow(Base):
    __tablename__ = "mp_attorneys"

    id = Column(String, primary_key=True, default=_uuid)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    bar_state = Column(String, nullable=True)
    bar_number = Column(String, nullable=True)
    bar_verified = Column(Boolean, default=False, nullable=False)
    bar_verified_at = Column(DateTime, nullable=True)
    specialties = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    location = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    hourly_rate_usd = Column(Integer, nullable=True)
    flat_rate_structure = Column(JSON, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now)

    assignments = relationship(
        "AttorneyAssignmentRow",
        back_populates="attorney",
        cascade="all, delete-orphan",
    )
    agreements = relationship(
        "LimitedScopeAgreementRow",
        back_populates="attorney",
        cascade="all, delete-orphan",
    )


class AttorneyAssignmentRow(Base):
    __tablename__ = "mp_attorney_assignments"

    id = Column(String, primary_key=True, default=_uuid)
    order_id = Column(String, ForeignKey("mp_orders.id"), nullable=False)
    attorney_id = Column(String, ForeignKey("mp_attorneys.id"), nullable=False)
    assigned_at = Column(DateTime, default=_now)
    reviewed_at = Column(DateTime, nullable=True)
    decision = Column(String, default="pending", nullable=False)
    checklist_responses = Column(JSON, nullable=True)
    attorney_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    order = relationship("OrderRow", back_populates="attorney_assignments")
    attorney = relationship("AttorneyRow", back_populates="assignments")


class EmailSequenceRow(Base):
    __tablename__ = "mp_email_sequences"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("mp_users.id"), nullable=False)
    sequence_name = Column(String, nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    next_send_at = Column(DateTime, default=_now, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)

    user = relationship("MarketplaceUserRow", back_populates="email_sequences")
