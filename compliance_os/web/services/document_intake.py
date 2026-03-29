"""Shared upload validation and doc-type resolution for v1 and v2 routes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compliance_os.web.services.classifier import (
    Classification,
    classify_file,
    is_auto_doc_type,
    normalize_doc_type,
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    DOCX_MIME_TYPE,
    "text/csv",
    "text/plain",
}


@dataclass
class ResolvedDocumentType:
    doc_type: str | None
    confidence: str | None
    source: str | None
    provided_doc_type: str | None = None


class UploadValidationError(ValueError):
    """Raised when an upload violates the shared intake policy."""

    def __init__(self, message: str, *, code: str = "upload_validation_failed"):
        super().__init__(message)
        self.code = code


def _is_disallowed_upload_name(filename: str | None) -> bool:
    if not filename:
        return False
    return Path(filename).name.startswith("~$")


def validate_upload(
    mime_type: str | None,
    content_size: int,
    *,
    filename: str | None = None,
) -> None:
    if mime_type not in ALLOWED_TYPES:
        raise UploadValidationError(
            f"File type {mime_type} not allowed",
            code="unsupported_mime_type",
        )
    if _is_disallowed_upload_name(filename):
        raise UploadValidationError(
            "Temporary Office lock files are not valid uploads",
            code="office_temp_artifact",
        )
    if content_size > MAX_FILE_SIZE:
        raise UploadValidationError("File exceeds 20MB limit", code="file_too_large")


def resolve_document_type(
    file_path: str,
    mime_type: str,
    *,
    provided_doc_type: str | None = None,
    allow_ocr: bool = False,
) -> ResolvedDocumentType:
    if provided_doc_type is not None and not is_auto_doc_type(provided_doc_type):
        normalized = normalize_doc_type(provided_doc_type)
        if normalized is None:
            raise UploadValidationError(f"Unsupported doc_type {provided_doc_type}")
        return ResolvedDocumentType(
            doc_type=normalized,
            confidence="high",
            source="user",
            provided_doc_type=provided_doc_type,
        )

    classification: Classification = classify_file(
        file_path,
        mime_type,
        allow_ocr=allow_ocr,
    )
    return ResolvedDocumentType(
        doc_type=classification.doc_type,
        confidence=classification.confidence,
        source=classification.source,
        provided_doc_type=provided_doc_type,
    )
