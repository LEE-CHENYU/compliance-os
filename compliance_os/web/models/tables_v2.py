"""Database tables for the Guardian check flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
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
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    documents = relationship("DocumentRow", back_populates="check", cascade="all, delete-orphan")
    comparisons = relationship("ComparisonRow", back_populates="check", cascade="all, delete-orphan")
    followups = relationship("FollowupRow", back_populates="check", cascade="all, delete-orphan")
    findings = relationship("FindingRow", back_populates="check", cascade="all, delete-orphan")
    ingestion_issues = relationship("IngestionIssueRow", back_populates="check", cascade="all, delete-orphan")


class DocumentRow(Base):
    __tablename__ = "documents_v2"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    doc_type = Column(String, nullable=False)
    document_family = Column(String, nullable=True)
    document_series_key = Column(String, nullable=True)
    document_version = Column(Integer, default=1)
    supersedes_document_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    filename = Column(String)
    source_path = Column(String, nullable=True)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    content_hash = Column(String(64), nullable=True)
    ocr_text = Column(Text, nullable=True)
    ocr_engine = Column(String, nullable=True)
    provenance = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime, default=_now)

    check = relationship("CheckRow", back_populates="documents")
    extracted_fields = relationship(
        "ExtractedFieldRow", back_populates="document", cascade="all, delete-orphan"
    )
    ingestion_issues = relationship(
        "IngestionIssueRow", back_populates="document", cascade="all, delete-orphan"
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


class IngestionIssueRow(Base):
    __tablename__ = "ingestion_issues"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents_v2.id"), nullable=True)
    stage = Column(String, nullable=False)
    issue_code = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    detected_at = Column(DateTime, default=_now)

    check = relationship("CheckRow", back_populates="ingestion_issues")
    document = relationship("DocumentRow", back_populates="ingestion_issues")


class LlmApiUsageRow(Base):
    __tablename__ = "llm_api_usage"

    id = Column(String, primary_key=True, default=_uuid)
    check_id = Column(String, ForeignKey("checks.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents_v2.id"), nullable=True)
    user_id = Column(String, nullable=True)
    environment = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    status = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cache_creation_input_tokens = Column(Integer, nullable=True)
    cache_read_input_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    request_metadata = Column(JSON, nullable=True)
    usage_details = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime, nullable=True)


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
