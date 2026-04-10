"""User model and auth schemas."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from pydantic import BaseModel

from compliance_os.web.models.tables_v2 import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRow(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    api_tokens = relationship("UserApiTokenRow", back_populates="user", cascade="all, delete-orphan")


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


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


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
