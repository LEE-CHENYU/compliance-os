"""Database tables for the Guardian check flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CheckRow(Base):
    __tablename__ = "checks"

    id = Column(String, primary_key=True, default=_uuid)
    track = Column(String, nullable=False)
    stage = Column(String, nullable=True)
    status = Column(String, default="intake")
    answers = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    documents = relationship("DocumentRow", back_populates="check", cascade="all, delete-orphan")
    comparisons = relationship("ComparisonRow", back_populates="check", cascade="all, delete-orphan")
    followups = relationship("FollowupRow", back_populates="check", cascade="all, delete-orphan")
    findings = relationship("FindingRow", back_populates="check", cascade="all, delete-orphan")


class DocumentRow(Base):
    __tablename__ = "documents_v2"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    doc_type = Column(String, nullable=False)
    filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    uploaded_at = Column(DateTime, default=_now)

    check = relationship("CheckRow", back_populates="documents")
    extracted_fields = relationship(
        "ExtractedFieldRow", back_populates="document", cascade="all, delete-orphan"
    )


class ExtractedFieldRow(Base):
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=_uuid)
    document_id = Column(String, ForeignKey("documents_v2.id"), nullable=False)
    field_name = Column(String, nullable=False)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    raw_text = Column(Text, nullable=True)

    document = relationship("DocumentRow", back_populates="extracted_fields")


class ComparisonRow(Base):
    __tablename__ = "comparisons"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    field_name = Column(String, nullable=False)
    value_a = Column(Text, nullable=True)
    value_b = Column(Text, nullable=True)
    match_type = Column(String)
    status = Column(String)
    confidence = Column(Float, nullable=True)
    detail = Column(Text, nullable=True)

    check = relationship("CheckRow", back_populates="comparisons")


class FollowupRow(Base):
    __tablename__ = "followups"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    question_key = Column(String, nullable=False)
    question_text = Column(Text, nullable=True)
    chips = Column(JSON, nullable=True)
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    check = relationship("CheckRow", back_populates="followups")


class FindingRow(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    rule_version = Column(String, nullable=True)
    severity = Column(String)
    category = Column(String)
    title = Column(Text)
    action = Column(Text)
    consequence = Column(String)
    immigration_impact = Column(Boolean, default=False)
    source_comparison_id = Column(String, ForeignKey("comparisons.id"), nullable=True)

    check = relationship("CheckRow", back_populates="findings")
