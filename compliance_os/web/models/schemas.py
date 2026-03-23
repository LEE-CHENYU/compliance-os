"""Pydantic models for API request/response serialization."""

from datetime import datetime

from pydantic import BaseModel


# --- Cases ---

class CaseCreate(BaseModel):
    workflow_type: str = ""

class CaseResponse(BaseModel):
    id: str
    workflow_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    answer_count: int = 0

class CaseListResponse(BaseModel):
    cases: list[CaseResponse]


# --- Discovery ---

class DiscoveryAnswerCreate(BaseModel):
    step: str
    question_key: str
    answer: dict | list | str

class DiscoveryAnswerResponse(BaseModel):
    id: str
    step: str
    question_key: str
    answer: dict | list | str
    answered_at: datetime

class DiscoveryAnswersResponse(BaseModel):
    answers: list[DiscoveryAnswerResponse]

class CaseSummary(BaseModel):
    summary: dict


# --- Chat ---

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]


# --- Documents ---

class DocumentSlot(BaseModel):
    key: str
    label: str
    required: bool = True
    group: str = "General"
    repeatable: bool = False

class DocumentChecklistResponse(BaseModel):
    slots: list[DocumentSlot]
    filled: dict[str, str] = {}

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str
    slot_key: str | None
    classification: str | None
    status: str
    uploaded_at: datetime

class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]

class DocumentUpdateRequest(BaseModel):
    slot_key: str | None = None
    classification: str | None = None
