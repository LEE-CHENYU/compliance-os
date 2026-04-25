"""SQLAlchemy ORM table definitions."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compliance_os.web.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CaseRow(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_type: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="discovery")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    discovery_answers: Mapped[list["DiscoveryAnswerRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessageRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    documents: Mapped[list["DocumentRow"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    professional_searches: Mapped[list["ProfessionalSearchRequestRow"]] = relationship(
        back_populates="case",
        order_by="ProfessionalSearchRequestRow.created_at.desc()",
    )


class DiscoveryAnswerRow(Base):
    __tablename__ = "discovery_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    step: Mapped[str] = mapped_column(String(50), nullable=False)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    answer: Mapped[dict] = mapped_column(JSON, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["CaseRow"] = relationship(back_populates="discovery_answers")


class ChatMessageRow(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["CaseRow"] = relationship(back_populates="chat_messages")


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    slot_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped["CaseRow"] = relationship(back_populates="documents")


class ProfessionalSearchRequestRow(Base):
    """User-initiated search for professionals (attorneys / CPAs / bankers).

    Populated by `POST /api/professional-search`, driven to completion by
    the runner in `services/professional_search_runner.py`. `status`
    transitions: queued → running → (complete | failed). Per-persona
    progress and the final tier report are JSON blobs so the shape can
    evolve without migrations.
    """

    __tablename__ = "professional_search_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.id"), nullable=True)
    case_brief: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    vertical: Mapped[str] = mapped_column(String(64), default="immigration_attorney")
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|complete|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Per-persona: { persona_id: { status, started_at, finished_at, output_path, error } }
    persona_status: Mapped[dict] = mapped_column(JSON, default=dict)

    # Final rendered tier report (list of rows from v_attorney_comparison)
    tier_report: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Full firm dossiers (deduped + merged across personas) — the rich data
    # backing the HTML/PDF reports. Stored in the DB so reports are
    # reproducible regardless of filesystem state. Each entry has all
    # original firm fields plus `_personas`, `_why_fits`, `_credentials`,
    # `_risks`, `_sources` (deduped).
    firms_data: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Uploaded-doc text snippets appended to the brief before dispatch
    uploaded_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stripe paywall — pay-first, claim-into-account-after.
    # `paid_at` is the source of truth for "report is unlocked"; set by the
    # Stripe webhook on `checkout.session.completed`.
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Email captured from Stripe at checkout — used to match a purchase to
    # an existing user, or to pre-fill signup when claiming post-purchase.
    stripe_customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # Set when an authenticated user claims a paid search via /claim. Null
    # until claimed — the row can exist (and be paid) without a user.
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped["CaseRow | None"] = relationship(back_populates="professional_searches")
