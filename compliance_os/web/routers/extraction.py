"""Document upload, LLM extraction, extraction results."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas_v2 import (
    DocumentExtraction,
    DocumentOut,
    IngestionIssue,
    LlmApiUsage,
)
from compliance_os.web.models.tables_v2 import (
    CheckRow,
    DocumentRow,
    IngestionIssueRow,
    LlmApiUsageRow,
)
from compliance_os.web.services.document_intake import (
    UploadValidationError,
    resolve_document_type,
    validate_upload,
)
from compliance_os.web.services.document_store import (
    document_series_key_for_document,
    extract_into_document,
    register_uploaded_document,
)
from compliance_os.web.services.ingestion_detector import (
    DetectedIssue,
    detect_upload_issues,
    extraction_failure_issue,
    record_check_issue,
    sync_document_issues,
)

UPLOAD_DIR = Path(__file__).parents[3] / "uploads"

router = APIRouter(prefix="/api/checks/{check_id}", tags=["extraction"])


def _normalized_uploaded_at(doc: DocumentRow) -> datetime:
    uploaded_at = doc.uploaded_at
    if uploaded_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if uploaded_at.tzinfo is None:
        return uploaded_at.replace(tzinfo=timezone.utc)
    return uploaded_at


@router.post("/documents", response_model=DocumentOut)
def upload_document(
    check_id: str,
    doc_type: str | None = Form(None),
    source_path: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    upload_dir = UPLOAD_DIR / check_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / filename
    content = file.file.read()
    try:
        validate_upload(file.content_type, len(content), filename=file.filename)
    except UploadValidationError as exc:
        record_check_issue(
            db,
            check=check,
            document=None,
            stage="upload_validation",
            issue=DetectedIssue(
                issue_code=getattr(exc, "code", "upload_validation_failed"),
                severity="error",
                message=str(exc),
                details={
                    "filename": file.filename,
                    "mime_type": file.content_type,
                    "content_size": len(content),
                },
            ),
        )
        db.commit()
        status = 413 if "20MB" in str(exc) else 400
        raise HTTPException(status, str(exc))
    file_path.write_bytes(content)

    try:
        resolved_doc_type = resolve_document_type(
            str(file_path),
            file.content_type or "application/octet-stream",
            provided_doc_type=doc_type,
            allow_ocr=False,
        )
    except UploadValidationError as exc:
        record_check_issue(
            db,
            check=check,
            document=None,
            stage="upload_detection",
            issue=DetectedIssue(
                issue_code=getattr(exc, "code", "doc_type_validation_failed"),
                severity="error",
                message=str(exc),
                details={
                    "filename": file.filename,
                    "provided_doc_type": doc_type,
                },
            ),
        )
        db.commit()
        raise HTTPException(400, str(exc))
    if not resolved_doc_type.doc_type:
        record_check_issue(
            db,
            check=check,
            document=None,
            stage="upload_detection",
            issue=DetectedIssue(
                issue_code="doc_type_unresolved",
                severity="error",
                message="Could not determine document type on the fast path; manual review is required.",
                details={
                    "filename": file.filename,
                    "source_path": source_path,
                    "mime_type": file.content_type,
                },
            ),
        )
        db.commit()
        raise HTTPException(400, "Could not determine document type; provide doc_type")

    row = DocumentRow(
        check_id=check_id,
        doc_type=resolved_doc_type.doc_type,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        provenance={
            "classification": {
                "doc_type": resolved_doc_type.doc_type,
                "source": resolved_doc_type.source,
                "confidence": resolved_doc_type.confidence,
                "provided_doc_type": resolved_doc_type.provided_doc_type,
            }
        },
    )
    db.add(row)
    db.flush()
    register_uploaded_document(check, row, content, source_path=source_path)
    sync_document_issues(
        db,
        check=check,
        document=row,
        stage="upload",
        issues=detect_upload_issues(
            doc_type=row.doc_type,
            filename=row.filename,
            source_path=row.source_path,
            mime_type=row.mime_type,
            classification_source=resolved_doc_type.source,
            provided_doc_type=resolved_doc_type.provided_doc_type,
            provenance=row.provenance,
        ),
    )
    check.status = "uploaded"
    db.commit()
    db.refresh(row)
    return row


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return check.documents


@router.post("/extract", response_model=dict)
def run_extraction(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    results = []
    for doc in check.documents:
        try:
            results.append(extract_into_document(doc, db))
        except Exception as exc:
            sync_document_issues(
                db,
                check=check,
                document=doc,
                stage="extraction",
                issues=[extraction_failure_issue(exc)],
            )
            db.commit()
            raise

    check.status = "extracted"
    db.commit()
    return {"status": "extracted", "documents": results}


@router.get("/ingestion-issues", response_model=list[IngestionIssue])
def list_ingestion_issues(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return (
        db.query(IngestionIssueRow)
        .filter(IngestionIssueRow.check_id == check_id)
        .order_by(IngestionIssueRow.detected_at.asc(), IngestionIssueRow.id.asc())
        .all()
    )


@router.get("/llm-usage", response_model=list[LlmApiUsage])
def list_llm_usage(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")
    return (
        db.query(LlmApiUsageRow)
        .filter(LlmApiUsageRow.check_id == check_id)
        .order_by(LlmApiUsageRow.started_at.desc(), LlmApiUsageRow.id.desc())
        .all()
    )


@router.get("/extractions", response_model=list[DocumentExtraction])
def get_extractions(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    return [
        {
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "document_family": doc.document_family,
            "document_series_key": doc.document_series_key or document_series_key_for_document(doc),
            "document_version": doc.document_version or 1,
            "is_active": doc.is_active is not False,
            "filename": doc.filename,
            "source_path": doc.source_path,
            "uploaded_at": doc.uploaded_at,
            "ocr_engine": doc.ocr_engine,
            "provenance": doc.provenance or {},
            "extracted_fields": doc.extracted_fields,
        }
        for doc in sorted(
            check.documents,
            key=lambda row: (_normalized_uploaded_at(row), row.document_version or 1, row.id),
        )
    ]
