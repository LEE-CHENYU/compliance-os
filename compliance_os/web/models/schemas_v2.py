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
    filename: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ExtractedField(BaseModel):
    id: str
    document_id: str
    field_name: str
    field_value: str | None
    confidence: float | None

    class Config:
        from_attributes = True


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
    comparisons: list[Comparison]
    findings: list[Finding]
    followups: list[Followup]
    advisories: list[Finding]
