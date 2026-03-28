"""Persisted ingestion issue detection for upload and extraction flows."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, IngestionIssueRow
from compliance_os.web.services.extractor import SCHEMAS


@dataclass(slots=True)
class DetectedIssue:
    issue_code: str
    severity: str
    message: str
    details: dict[str, Any] | None = None


_SEVERITY_ORDER = {"info": 1, "warning": 2, "error": 3}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_stem(value: str | None) -> str:
    if not value:
        return ""
    stem = Path(value).stem.lower().strip()
    stem = re.sub(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_",
        "",
        stem,
    )
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return stem


def _is_generic_signal(value: str | None) -> bool:
    normalized = _normalized_stem(value)
    if not normalized:
        return True

    generic_patterns = (
        r"img_\d+$",
        r"image_\d+$",
        r"photo_\d+$",
        r"scan(?:ned)?(?:_\d+)?$",
        r"document(?:_\d+)?$",
        r"file(?:_\d+)?$",
        r"upload(?:ed)?(?:_\d+)?$",
        r"unnamed(?:_\d+)?$",
        r"wechatimg\d+$",
        r"weixin_image_\d+$",
        r"whatsapp_image_\d{4}_\d{2}_\d{2}_at_.*$",
        r"\d+$",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in generic_patterns)


def detect_upload_issues(
    *,
    doc_type: str | None,
    filename: str | None,
    source_path: str | None,
    mime_type: str | None,
    classification_source: str | None,
    provided_doc_type: str | None,
    provenance: dict[str, Any] | None = None,
) -> list[DetectedIssue]:
    issues: list[DetectedIssue] = []

    if doc_type is None:
        issues.append(
            DetectedIssue(
                issue_code="doc_type_unresolved",
                severity="error",
                message="Upload could not be classified on the fast path and needs manual review.",
                details={
                    "filename": filename,
                    "source_path": source_path,
                    "mime_type": mime_type,
                    "classification_source": classification_source,
                },
            )
        )
        return issues

    filename_generic = _is_generic_signal(filename)
    source_generic = _is_generic_signal(source_path)
    if filename_generic and (not source_path or source_generic):
        issues.append(
            DetectedIssue(
                issue_code="generic_source_name",
                severity="warning",
                message="Upload used a generic filename without descriptive source context.",
                details={
                    "filename": filename,
                    "source_path": source_path,
                },
            )
        )

    if mime_type in {"image/png", "image/jpeg"} and (not source_path or source_generic):
        issues.append(
            DetectedIssue(
                issue_code="image_context_low_signal",
                severity="warning",
                message="Image upload lacks descriptive source context and may need manual intake review.",
                details={
                    "filename": filename,
                    "source_path": source_path,
                    "classification_source": classification_source,
                },
            )
        )

    if doc_type not in SCHEMAS:
        issues.append(
            DetectedIssue(
                issue_code="structured_extraction_unsupported",
                severity="warning",
                message="Document type is classified but does not yet have a structured extraction schema.",
                details={
                    "doc_type": doc_type,
                    "provided_doc_type": provided_doc_type,
                },
            )
        )

    duplicate_of = ((provenance or {}).get("upload") or {}).get("duplicate_of_document_id")
    if duplicate_of:
        issues.append(
            DetectedIssue(
                issue_code="duplicate_upload",
                severity="info",
                message="Upload duplicates an earlier document version.",
                details={"duplicate_of_document_id": duplicate_of},
            )
        )

    return issues


def detect_extraction_issues(
    *,
    doc_type: str,
    text: str,
    fields: dict[str, dict[str, Any]],
) -> list[DetectedIssue]:
    issues: list[DetectedIssue] = []
    normalized_text = re.sub(r"\s+", " ", text or "").strip()

    if len(normalized_text) < 40:
        issues.append(
            DetectedIssue(
                issue_code="ocr_text_too_short",
                severity="warning",
                message="OCR or text extraction returned too little text for reliable structured extraction.",
                details={"text_length": len(normalized_text)},
            )
        )

    if doc_type in SCHEMAS:
        non_empty_values = [
            payload.get("value")
            for payload in fields.values()
            if payload.get("value") not in (None, "", [], {})
        ]
        if not non_empty_values:
            issues.append(
                DetectedIssue(
                    issue_code="no_structured_fields_extracted",
                    severity="warning",
                    message="Structured extraction completed but did not produce any populated fields.",
                    details={"doc_type": doc_type, "field_count": len(fields)},
                )
            )

    return issues


def extraction_failure_issue(exc: Exception) -> DetectedIssue:
    return DetectedIssue(
        issue_code="extraction_failed",
        severity="error",
        message="Structured extraction failed for the uploaded document.",
        details={"error": str(exc)},
    )


def record_check_issue(
    db: Session,
    *,
    check: CheckRow,
    document: DocumentRow | None,
    stage: str,
    issue: DetectedIssue,
) -> IngestionIssueRow:
    row = IngestionIssueRow(
        check_id=check.id,
        document_id=document.id if document is not None else None,
        stage=stage,
        issue_code=issue.issue_code,
        severity=issue.severity,
        message=issue.message,
        details=issue.details,
    )
    db.add(row)
    db.flush()
    if document is not None:
        _update_document_issue_summary(db, document)
    return row


def sync_document_issues(
    db: Session,
    *,
    check: CheckRow,
    document: DocumentRow,
    stage: str,
    issues: list[DetectedIssue],
) -> None:
    existing = (
        db.query(IngestionIssueRow)
        .filter(
            IngestionIssueRow.check_id == check.id,
            IngestionIssueRow.document_id == document.id,
            IngestionIssueRow.stage == stage,
        )
        .all()
    )
    existing_by_code = {row.issue_code: row for row in existing}
    wanted_codes = {issue.issue_code for issue in issues}

    for row in existing:
        if row.issue_code not in wanted_codes:
            db.delete(row)

    for issue in issues:
        row = existing_by_code.get(issue.issue_code)
        if row is None:
            db.add(
                IngestionIssueRow(
                    check_id=check.id,
                    document_id=document.id,
                    stage=stage,
                    issue_code=issue.issue_code,
                    severity=issue.severity,
                    message=issue.message,
                    details=issue.details,
                )
            )
            continue
        row.severity = issue.severity
        row.message = issue.message
        row.details = issue.details
        row.detected_at = datetime.now(timezone.utc)

    db.flush()
    _update_document_issue_summary(db, document)


def _update_document_issue_summary(db: Session, document: DocumentRow) -> None:
    rows = (
        db.query(IngestionIssueRow)
        .filter(IngestionIssueRow.document_id == document.id)
        .order_by(IngestionIssueRow.detected_at.asc(), IngestionIssueRow.id.asc())
        .all()
    )
    severity = "info"
    for row in rows:
        if _SEVERITY_ORDER.get(row.severity, 0) > _SEVERITY_ORDER.get(severity, 0):
            severity = row.severity

    by_stage: dict[str, int] = {}
    for row in rows:
        by_stage[row.stage] = by_stage.get(row.stage, 0) + 1

    provenance = dict(document.provenance or {})
    provenance["ingestion_detection"] = {
        "issue_count": len(rows),
        "severity": severity if rows else None,
        "issue_codes": [row.issue_code for row in rows],
        "by_stage": by_stage,
        "updated_at": _now_iso(),
    }
    document.provenance = provenance
