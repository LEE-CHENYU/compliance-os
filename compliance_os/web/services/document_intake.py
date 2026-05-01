"""Shared upload validation and doc-type resolution for v1 and v2 routes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from compliance_os.web.services.classifier import (
    Classification,
    classify_file,
    classify_filename,
    classify_text,
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
    # Filename + text classifications computed independently. Set by
    # `detect_filename_content_mismatch`; allows the upload route to
    # emit an `ingestion_issue` when the two disagree (a common signal
    # that the file is mislabeled — e.g. an "affidavit" filename
    # wrapping an I-20 PDF).
    filename_doc_type: str | None = None
    text_doc_type: str | None = None
    has_mismatch: bool = False


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


def detect_filename_content_mismatch(
    file_path: str,
    mime_type: str,
    resolved: ResolvedDocumentType,
) -> ResolvedDocumentType:
    """Annotate `resolved` with separate filename + text classifications.

    The default cascade (`classify_file`) returns the *first* match
    across filename → text → OCR, so a filename that wins doesn't tell
    us whether the content would have classified differently. This
    helper runs both passes independently and stamps the comparison
    onto the resolved type. The caller can then emit an ingestion
    issue when they disagree.

    Skipped when the user supplied an explicit doc_type (their choice
    wins; we don't second-guess them).
    """
    if resolved.source == "user":
        return resolved

    fname_cls = classify_filename(file_path)
    text_cls = Classification(doc_type=None, confidence=None)
    if mime_type == "application/pdf":
        try:
            from compliance_os.web.services.pdf_reader import extract_first_page

            text = extract_first_page(file_path)
            if text:
                text_cls = classify_text(text)
        except Exception:
            pass
    elif mime_type == DOCX_MIME_TYPE:
        try:
            from compliance_os.web.services.docx_reader import extract_docx_text

            text, _ = extract_docx_text(file_path)
            if text:
                text_cls = classify_text(text)
        except Exception:
            pass
    elif mime_type in {"text/plain", "text/csv"}:
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            if text:
                text_cls = classify_text(text)
        except Exception:
            pass

    resolved.filename_doc_type = fname_cls.doc_type
    resolved.text_doc_type = text_cls.doc_type
    resolved.has_mismatch = bool(
        fname_cls.doc_type
        and text_cls.doc_type
        and fname_cls.doc_type != text_cls.doc_type
    )
    return resolved
