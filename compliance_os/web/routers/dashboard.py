"""Dashboard API — timeline, stats, upload, documents."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import DATA_DIR, get_session
from compliance_os.web.models.schemas_v2 import SubjectChain
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.auth_service import decode_token
from compliance_os.web.services.document_intake import (
    UploadValidationError,
    resolve_document_type,
    validate_upload,
)
from compliance_os.web.services.document_store import (
    content_hash_for_bytes,
    extract_into_document,
    find_user_duplicate_documents,
    register_uploaded_document,
    serialize_duplicate_document,
)
from compliance_os.web.services.ingestion_detector import (
    DetectedIssue,
    detect_upload_issues,
    extraction_failure_issue,
    record_check_issue,
    sync_document_issues,
)
from compliance_os.web.services.subject_chains import (
    list_user_subject_chains,
    serialize_subject_chain,
    sync_user_subject_chains,
)
from compliance_os.web.services.timeline_builder import (
    build_stats,
    build_timeline,
    canonical_documents_for_checks,
    serialize_dashboard_document,
)

UPLOAD_DIR = DATA_DIR / "uploads"

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

ALLOWED_DUPLICATE_ACTIONS = {"ask", "keep", "skip"}


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization")
    payload = decode_token(authorization.split(" ", 1)[1])
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _ensure_dashboard_check(user: UserRow, db: Session) -> CheckRow:
    check = db.query(CheckRow).filter(
        CheckRow.user_id == user.id,
        CheckRow.status == "saved",
    ).first()
    if check:
        return check
    check = CheckRow(track="stem_opt", status="saved", user_id=user.id, answers={})
    db.add(check)
    db.flush()
    return check


def _parse_source_paths_json(source_paths_json: str | None, expected_length: int) -> list[str | None]:
    if not source_paths_json:
        return [None] * expected_length
    try:
        raw = json.loads(source_paths_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid source_paths_json: {exc.msg}") from exc
    if not isinstance(raw, list):
        raise HTTPException(400, "source_paths_json must be a JSON array")
    if len(raw) != expected_length:
        raise HTTPException(400, "source_paths_json length must match number of files")
    normalized: list[str | None] = []
    for item in raw:
        normalized.append(str(item) if item not in (None, "") else None)
    return normalized


def _resolve_upload_duplicate_candidates(db: Session, *, user_id: str, content_hash: str) -> list[dict[str, Any]]:
    return [
        serialize_duplicate_document(doc)
        for doc in find_user_duplicate_documents(db, user_id=user_id, content_hash=content_hash)
    ]


def _resolve_doc_type_for_upload_file(
    *,
    upload_dir: Path,
    file_name: str,
    content: bytes,
    mime_type: str,
    provided_doc_type: str | None,
) -> Any:
    temp_path = upload_dir / f".preflight_{uuid.uuid4()}_{file_name}"
    temp_path.write_bytes(content)
    try:
        return resolve_document_type(
            str(temp_path),
            mime_type,
            provided_doc_type=provided_doc_type,
            allow_ocr=False,
        )
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/timeline")
def get_timeline(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    sync_user_subject_chains(user.id, db)
    payload = build_timeline(user.id, db)
    db.commit()
    return payload


@router.get("/stats")
def get_stats(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    return build_stats(user.id, db)


@router.get("/chains", response_model=list[SubjectChain])
def list_subject_chains(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    sync_user_subject_chains(user.id, db)
    chains = [serialize_subject_chain(chain) for chain in list_user_subject_chains(user.id, db)]
    db.commit()
    return chains


@router.get("/documents")
def list_documents(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    checks = db.query(CheckRow).filter(CheckRow.user_id == user.id).all()
    return [serialize_dashboard_document(doc) for doc in canonical_documents_for_checks(checks)]


@router.get("/documents/{doc_id}/view")
def view_document(
    doc_id: str,
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Download/view a document by ID."""
    user = _get_user(authorization, db)
    # Find the document and verify it belongs to this user
    from compliance_os.web.models.tables_v2 import DocumentRow as DocRow
    doc = db.get(DocRow, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    check = db.get(CheckRow, doc.check_id)
    if not check or check.user_id != user.id:
        raise HTTPException(403, "Not authorized")
    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.post("/upload")
def upload_to_dataroom(
    doc_type: str | None = Form(None),
    source_path: str | None = Form(None),
    duplicate_action: str = Form("ask"),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Upload a document to the data room. Auto-extracts and re-evaluates."""
    user = _get_user(authorization, db)
    if duplicate_action not in ALLOWED_DUPLICATE_ACTIONS:
        raise HTTPException(400, "duplicate_action must be one of ask, keep, skip")

    # Find or create a check to attach this document to
    check = _ensure_dashboard_check(user, db)

    # Save file
    upload_dir = UPLOAD_DIR / check.id
    upload_dir.mkdir(parents=True, exist_ok=True)
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
    try:
        resolved_doc_type = _resolve_doc_type_for_upload_file(
            upload_dir=upload_dir,
            file_name=file.filename or "upload",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
            provided_doc_type=doc_type,
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
    content_hash = content_hash_for_bytes(content)
    duplicate_candidates = _resolve_upload_duplicate_candidates(db, user_id=user.id, content_hash=content_hash)
    if duplicate_candidates and duplicate_action == "ask":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_upload_detected",
                "message": "This file matches a document already in your data room.",
                "content_hash": content_hash,
                "duplicates": duplicate_candidates,
                "resolved_doc_type": resolved_doc_type.doc_type,
            },
        )
    if duplicate_candidates and duplicate_action == "skip":
        return {
            "ok": True,
            "status": "skipped_duplicate",
            "content_hash": content_hash,
            "duplicates": duplicate_candidates,
            "resolved_doc_type": resolved_doc_type.doc_type,
        }

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / filename
    file_path.write_bytes(content)
    if not resolved_doc_type.doc_type:
        file_path.unlink(missing_ok=True)
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

    # Create document record
    doc = DocumentRow(
        check_id=check.id,
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
    db.add(doc)
    db.flush()
    register_uploaded_document(check, doc, content, source_path=source_path, db=db)
    sync_document_issues(
        db,
        check=check,
        document=doc,
        stage="upload",
        issues=detect_upload_issues(
            doc_type=doc.doc_type,
            filename=doc.filename,
            source_path=doc.source_path,
            mime_type=doc.mime_type,
            classification_source=resolved_doc_type.source,
            provided_doc_type=resolved_doc_type.provided_doc_type,
            provenance=doc.provenance,
        ),
    )
    db.commit()
    db.refresh(doc)

    # Auto-extract
    try:
        extract_into_document(doc, db)
        db.commit()
    except Exception as exc:
        sync_document_issues(
            db,
            check=check,
            document=doc,
            stage="extraction",
            issues=[extraction_failure_issue(exc)],
        )
        db.commit()

    # Re-evaluate all checks for this user
    from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

    for user_check in db.query(CheckRow).filter(CheckRow.user_id == user.id).all():
        try:
            rule_file = Path(__file__).resolve().parents[3] / "config" / "rules" / f"{user_check.track}.yaml"
            if not rule_file.exists():
                continue
            engine = RuleEngine.from_yaml(str(rule_file))

            # Build context
            ext_a, ext_b = {}, {}
            for d in user_check.documents:
                fields = {f.field_name: f.field_value for f in d.extracted_fields}
                if d.doc_type in ("i983",):
                    ext_a = fields
                else:
                    ext_b = fields

            comp_dict = {c.field_name: {"status": c.status, "confidence": c.confidence} for c in user_check.comparisons}

            ctx = EvaluationContext(
                answers=user_check.answers or {},
                extraction_a=ext_a,
                extraction_b=ext_b,
                comparisons=comp_dict,
            )

            # Clear old findings and re-evaluate
            for old in user_check.findings:
                db.delete(old)

            from compliance_os.web.models.tables_v2 import FindingRow
            for fr in engine.evaluate(ctx):
                db.add(FindingRow(
                    check_id=user_check.id,
                    rule_id=fr.rule_id,
                    rule_version=engine.version,
                    severity=fr.severity,
                    category=fr.category,
                    title=fr.title,
                    action=fr.action,
                    consequence=fr.consequence,
                    immigration_impact=fr.immigration_impact,
                ))
            db.commit()
        except Exception:
            pass

    return {
        "ok": True,
        "status": "uploaded",
        "document_id": doc.id,
        "content_hash": content_hash,
        "duplicates": duplicate_candidates,
    }


@router.post("/upload/prepare")
def prepare_dataroom_upload(
    doc_type: str | None = Form(None),
    source_paths_json: str | None = Form(None),
    files: list[UploadFile] = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Preflight one or more uploads and flag duplicates before storing."""
    user = _get_user(authorization, db)
    check = _ensure_dashboard_check(user, db)
    upload_dir = UPLOAD_DIR / check.id
    upload_dir.mkdir(parents=True, exist_ok=True)
    source_paths = _parse_source_paths_json(source_paths_json, len(files))

    results: list[dict[str, Any]] = []
    for index, upload in enumerate(files):
        content = upload.file.read()
        source_path = source_paths[index]
        entry: dict[str, Any] = {
            "file_name": upload.filename,
            "source_path": source_path,
            "mime_type": upload.content_type or "application/octet-stream",
            "file_size": len(content),
            "resolved_doc_type": None,
            "classification_source": None,
            "confidence": None,
            "status": "ready",
            "message": None,
            "content_hash": None,
            "duplicates": [],
        }
        try:
            validate_upload(upload.content_type, len(content), filename=upload.filename)
        except UploadValidationError as exc:
            entry["status"] = "invalid"
            entry["message"] = str(exc)
            results.append(entry)
            continue

        try:
            resolved = _resolve_doc_type_for_upload_file(
                upload_dir=upload_dir,
                file_name=upload.filename or "upload",
                content=content,
                mime_type=upload.content_type or "application/octet-stream",
                provided_doc_type=doc_type,
            )
        except UploadValidationError as exc:
            entry["status"] = "invalid"
            entry["message"] = str(exc)
            results.append(entry)
            continue
        entry["resolved_doc_type"] = resolved.doc_type
        entry["classification_source"] = resolved.source
        entry["confidence"] = resolved.confidence
        if not resolved.doc_type:
            entry["status"] = "unresolved"
            entry["message"] = "Could not determine document type on the fast path."
            results.append(entry)
            continue

        content_hash = content_hash_for_bytes(content)
        entry["content_hash"] = content_hash
        duplicates = _resolve_upload_duplicate_candidates(db, user_id=user.id, content_hash=content_hash)
        if duplicates:
            entry["status"] = "duplicate"
            entry["message"] = "This file already exists in your data room."
            entry["duplicates"] = duplicates
        results.append(entry)

    return {"files": results}
