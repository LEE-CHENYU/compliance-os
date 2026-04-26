"""User model and auth schemas."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from pydantic import BaseModel, field_validator

from compliance_os.web.models.tables_v2 import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("Enter a valid email address")
    return normalized


class UserRow(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    api_tokens = relationship("UserApiTokenRow", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship(
        "SubscriptionRow",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="SubscriptionRow.created_at.desc()",
    )


class UserApiTokenRow(Base):
    __tablename__ = "user_api_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_type = Column(String, nullable=False, default="openclaw")
    label = Column(String, nullable=False, default="OpenClaw")
    scope = Column(String, nullable=False, default="openclaw")
    token_prefix = Column(String, unique=True, nullable=False)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("UserRow", back_populates="api_tokens")


class SubscriptionRow(Base):
    """Mirror of a Stripe Subscription, scoped to a Guardian user.

    Source of truth is Stripe — this row is rebuilt from
    `customer.subscription.*` webhooks. App code never mutates Stripe
    state directly; it only reads this mirror via `subscription_service`.

    `tier` is derived: `pro_trial` while `status=trialing`, else `pro`.
    `status=canceled` rows are kept for audit but treated as no
    entitlement — `is_pro()` requires a non-canceled active/trialing row.
    """

    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Stripe identifiers. customer_id is set on first checkout; subscription_id
    # is set when the trial/sub is actually created (a step later).
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    stripe_price_id = Column(String, nullable=True)

    # Stripe-mirrored state. We store both the raw status and the derived
    # tier so router code doesn't need to recompute on every request.
    status = Column(String, nullable=False)
    # 'pro_trial' | 'pro'
    tier = Column(String, nullable=False)

    # Period bookkeeping (UTC).
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    user = relationship("UserRow", back_populates="subscriptions")


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    role: str


class OpenClawTokenInfo(BaseModel):
    label: str
    token_type: str
    scope: str
    token_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None

    class Config:
        from_attributes = True


class OpenClawConnectionStatus(BaseModel):
    api_url: str
    install_command: str
    env_var: str
    token_type: str
    scope: str
    active_token: OpenClawTokenInfo | None = None


class OpenClawTokenIssueResponse(OpenClawConnectionStatus):
    token: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
