"""Pydantic schemas for the Guardian check flow API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CheckCreate(BaseModel):
    track: str
    answers: dict[str, Any] = {}


class CheckUpdate(BaseModel):
    answers: dict[str, Any] | None = None
    status: str | None = None


class Check(BaseModel):
    id: str
    track: str
    stage: str | None
    status: str
    answers: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    check_id: str
    doc_type: str
    document_family: str | None = None
    document_series_key: str | None = None
    document_version: int = 1
    supersedes_document_id: str | None = None
    is_active: bool = True
    filename: str
    source_path: str | None = None
    file_size: int
    mime_type: str
    content_hash: str | None = None
    ocr_engine: str | None = None
    provenance: dict[str, Any] | None = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ExtractedField(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: str | None
    confidence: float | None
    raw_text: str | None = None

    class Config:
        from_attributes = True


class IngestionIssue(BaseModel):
    id: str
    check_id: str
    document_id: str | None = None
    stage: str
    issue_code: str
    severity: str
    message: str
    details: dict[str, Any] | None = None
    detected_at: datetime

    class Config:
        from_attributes = True


class LlmApiUsage(BaseModel):
    id: str
    check_id: str | None = None
    document_id: str | None = None
    user_id: str | None = None
    environment: str
    provider: str
    model: str
    operation: str
    status: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    latency_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    request_metadata: dict[str, Any] | None = None
    usage_details: dict[str, Any] | None = None
    started_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class DocumentExtraction(BaseModel):
    document_id: str
    doc_type: str
    document_family: str | None = None
    document_series_key: str | None = None
    document_version: int = 1
    is_active: bool = True
    filename: str
    source_path: str | None = None
    uploaded_at: datetime | None = None
    ocr_engine: str | None = None
    provenance: dict[str, Any] | None = None
    extracted_fields: list[ExtractedField]


class Comparison(BaseModel):
    id: str
    check_id: str
    field_name: str
    value_a: str | None
    value_b: str | None
    match_type: str
    status: str
    confidence: float | None
    detail: str | None

    class Config:
        from_attributes = True


class Followup(BaseModel):
    id: str
    check_id: str
    question_key: str
    question_text: str | None
    chips: list[str] | None
    answer: str | None
    answered_at: datetime | None

    class Config:
        from_attributes = True


class FollowupAnswer(BaseModel):
    answer: str


class Finding(BaseModel):
    id: str
    check_id: str
    rule_id: str
    severity: str
    category: str
    title: str
    action: str
    consequence: str
    immigration_impact: bool

    class Config:
        from_attributes = True


class Snapshot(BaseModel):
    check: Check
    extractions: dict[str, list[ExtractedField]]
    document_extractions: list[DocumentExtraction] = []
    comparisons: list[Comparison]
    findings: list[Finding]
    followups: list[Followup]
    advisories: list[Finding]
