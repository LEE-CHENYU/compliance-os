"""Document upload and management API endpoints."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas import (
    DocumentChecklistResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
)
from compliance_os.web.models.tables import (
    CaseRow,
    DiscoveryAnswerRow,
    DocumentRow as CaseDocumentRow,
)
from compliance_os.web.models.tables_v2 import CheckRow as V2CheckRow
from compliance_os.web.models.tables_v2 import DocumentRow as V2DocumentRow
from compliance_os.web.services.checklist import generate_checklist
from compliance_os.web.services.classifier import normalize_doc_type
from compliance_os.web.services.document_intake import (
    UploadValidationError,
    resolve_document_type,
    validate_upload,
)
from compliance_os.web.services.ingestion_detector import (
    DetectedIssue,
    detect_upload_issues,
    record_check_issue,
    sync_document_issues,
)
from compliance_os.web.services.document_store import register_uploaded_document
from compliance_os.web.services.document_store import reindex_documents_for_doc_types

UPLOADS_DIR = Path(__file__).parents[3] / "uploads"
LEGACY_CASE_STAGE_PREFIX = "legacy_case:"
LEGACY_UNCLASSIFIED_DOC_TYPE = "unclassified"

router = APIRouter(prefix="/api/cases/{case_id}/documents", tags=["documents"])


def _get_case(case_id: str, session: Session) -> CaseRow:
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _legacy_case_stage(case_id: str) -> str:
    return f"{LEGACY_CASE_STAGE_PREFIX}{case_id}"


def _legacy_track_for_case(case: CaseRow) -> str:
    workflow = (case.workflow_type or "").strip().lower()
    if workflow in {"tax", "entity", "business", "corporate", "company"}:
        return "entity"
    if workflow in {"student", "cpt", "f1", "f-1"}:
        return "student"
    return "stem_opt"


def _get_or_create_v2_bridge_check(case: CaseRow, session: Session) -> V2CheckRow:
    stage = _legacy_case_stage(case.id)
    row = (
        session.query(V2CheckRow)
        .filter_by(stage=stage)
        .order_by(V2CheckRow.created_at.asc(), V2CheckRow.id.asc())
        .first()
    )
    if row:
        return row

    row = V2CheckRow(
        track=_legacy_track_for_case(case),
        stage=stage,
        status="uploaded",
        answers={
            "legacy_case_id": case.id,
            "legacy_workflow_type": case.workflow_type or "",
            "bridge_source": "api/cases/{case_id}/documents",
        },
    )
    session.add(row)
    session.flush()
    return row


def _find_mirrored_v2_document(
    *,
    case_id: str,
    file_path: str,
    session: Session,
) -> V2DocumentRow | None:
    bridge_check = (
        session.query(V2CheckRow)
        .filter_by(stage=_legacy_case_stage(case_id))
        .order_by(V2CheckRow.created_at.asc(), V2CheckRow.id.asc())
        .first()
    )
    if not bridge_check:
        return None
    return (
        session.query(V2DocumentRow)
        .filter_by(check_id=bridge_check.id, file_path=file_path)
        .order_by(V2DocumentRow.uploaded_at.desc(), V2DocumentRow.id.desc())
        .first()
    )


def _mirror_document_to_v2(
    *,
    case: CaseRow,
    safe_name: str,
    source_path: str,
    dest: Path,
    content: bytes,
    mime_type: str,
    classification_doc_type: str | None,
    classification_source: str | None,
    classification_confidence: str | None,
    classification_provided_doc_type: str | None,
    session: Session,
) -> V2DocumentRow:
    bridge_check = _get_or_create_v2_bridge_check(case, session)
    mirrored_doc_type = classification_doc_type or LEGACY_UNCLASSIFIED_DOC_TYPE
    row = V2DocumentRow(
        check_id=bridge_check.id,
        doc_type=mirrored_doc_type,
        filename=safe_name,
        source_path=source_path,
        file_path=str(dest),
        file_size=len(content),
        mime_type=mime_type,
        provenance={
            "classification": {
                "doc_type": classification_doc_type,
                "source": classification_source,
                "confidence": classification_confidence,
                "provided_doc_type": classification_provided_doc_type,
                "fallback_doc_type": (
                    mirrored_doc_type if classification_doc_type is None else None
                ),
            },
            "ingestion": {
                "route": "v1_case_documents",
                "legacy_case_id": case.id,
                "source_path": source_path,
            },
        },
    )
    session.add(row)
    session.flush()
    register_uploaded_document(bridge_check, row, content, source_path=source_path)
    return row


def _doc_response(d: CaseDocumentRow) -> DocumentResponse:
    return DocumentResponse(
        id=d.id, filename=d.filename, file_size=d.file_size,
        mime_type=d.mime_type, slot_key=d.slot_key,
        classification=d.classification, status=d.status,
        uploaded_at=d.uploaded_at,
    )


@router.get("/checklist", response_model=DocumentChecklistResponse)
def get_checklist(case_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    answers = session.query(DiscoveryAnswerRow).filter_by(case_id=case_id).all()
    answer_dicts = [{"question_key": a.question_key, "step": a.step, "answer": a.answer} for a in answers]
    slots = generate_checklist(answer_dicts)
    # Build filled map
    docs = session.query(CaseDocumentRow).filter_by(case_id=case_id).all()
    filled = {d.slot_key: d.id for d in docs if d.slot_key}
    return DocumentChecklistResponse(slots=slots, filled=filled)


@router.post("", response_model=DocumentResponse)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    doc_type: str | None = Form(None),
    source_path: str | None = Form(None),
    slot_key: str | None = Form(None),
    session: Session = Depends(get_session),
):
    case = _get_case(case_id, session)
    bridge_check = _get_or_create_v2_bridge_check(case, session)

    content = await file.read()
    try:
        validate_upload(file.content_type, len(content))
    except UploadValidationError as exc:
        record_check_issue(
            session,
            check=bridge_check,
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
                    "legacy_case_id": case.id,
                },
            ),
        )
        session.commit()
        status = 413 if "20MB" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))

    # Save file
    case_dir = UPLOADS_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_name = file.filename or "upload"
    dest = case_dir / f"{file_id}_{safe_name}"
    dest.write_bytes(content)

    # Classify
    # Keep upload latency predictable: classify conservatively from filename and
    # first-page PDF text only. Full OCR is reserved for the deeper v2 pipeline.
    try:
        classification_result = resolve_document_type(
            str(dest),
            file.content_type or "",
            provided_doc_type=doc_type,
            allow_ocr=False,
        )
    except UploadValidationError as exc:
        record_check_issue(
            session,
            check=bridge_check,
            document=None,
            stage="upload_detection",
            issue=DetectedIssue(
                issue_code=getattr(exc, "code", "doc_type_validation_failed"),
                severity="error",
                message=str(exc),
                details={
                    "filename": file.filename,
                    "provided_doc_type": doc_type,
                    "legacy_case_id": case.id,
                },
            ),
        )
        session.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    normalized_source_path = (source_path or "").strip() or safe_name

    mirrored = _mirror_document_to_v2(
        case=case,
        safe_name=safe_name,
        source_path=normalized_source_path,
        dest=dest,
        content=content,
        mime_type=file.content_type or "",
        classification_doc_type=classification_result.doc_type,
        classification_source=classification_result.source,
        classification_confidence=classification_result.confidence,
        classification_provided_doc_type=classification_result.provided_doc_type,
        session=session,
    )
    sync_document_issues(
        session,
        check=bridge_check,
        document=mirrored,
        stage="upload",
        issues=detect_upload_issues(
            doc_type=classification_result.doc_type,
            filename=mirrored.filename,
            source_path=mirrored.source_path,
            mime_type=mirrored.mime_type,
            classification_source=classification_result.source,
            provided_doc_type=classification_result.provided_doc_type,
            provenance=mirrored.provenance,
        ),
    )

    # Create record
    doc = CaseDocumentRow(
        case_id=case_id,
        filename=safe_name,
        file_path=str(dest),
        file_size=len(content),
        mime_type=file.content_type or "",
        slot_key=slot_key,
        classification=classification_result.doc_type,
        status="classified" if classification_result.doc_type else "uploaded",
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _doc_response(doc)


@router.get("", response_model=DocumentListResponse)
def list_documents(case_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    docs = (
        session.query(CaseDocumentRow)
        .filter_by(case_id=case_id)
        .order_by(CaseDocumentRow.uploaded_at)
        .all()
    )
    return DocumentListResponse(documents=[_doc_response(d) for d in docs])


@router.patch("/{doc_id}", response_model=DocumentResponse)
def update_document(case_id: str, doc_id: str, body: DocumentUpdateRequest, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    doc = session.get(CaseDocumentRow, doc_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if body.slot_key is not None:
        doc.slot_key = body.slot_key
    if body.classification is not None:
        normalized = normalize_doc_type(body.classification)
        if body.classification and normalized is None:
            raise HTTPException(status_code=400, detail=f"Unsupported classification {body.classification}")
        doc.classification = normalized
        mirrored = _find_mirrored_v2_document(
            case_id=case_id,
            file_path=doc.file_path,
            session=session,
        )
        if mirrored is not None:
            previous_doc_type = mirrored.doc_type
            mirrored.doc_type = normalized or LEGACY_UNCLASSIFIED_DOC_TYPE
            provenance = dict(mirrored.provenance or {})
            classification = dict(provenance.get("classification") or {})
            classification.update(
                {
                    "doc_type": normalized,
                    "source": "legacy_patch",
                    "confidence": "high" if normalized else None,
                    "provided_doc_type": body.classification,
                    "fallback_doc_type": (
                        LEGACY_UNCLASSIFIED_DOC_TYPE if normalized is None else None
                    ),
                }
            )
            provenance["classification"] = classification
            mirrored.provenance = provenance
            check = mirrored.check or session.get(V2CheckRow, mirrored.check_id)
            if check is not None:
                reindex_documents_for_doc_types(
                    check,
                    [previous_doc_type, mirrored.doc_type],
                )
    session.commit()
    session.refresh(doc)
    return _doc_response(doc)


@router.delete("/{doc_id}")
def delete_document(case_id: str, doc_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    doc = session.get(CaseDocumentRow, doc_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    # Delete file
    try:
        os.remove(doc.file_path)
    except OSError:
        pass

    mirrored = _find_mirrored_v2_document(
        case_id=case_id,
        file_path=doc.file_path,
        session=session,
    )
    if mirrored is not None:
        check = mirrored.check or session.get(V2CheckRow, mirrored.check_id)
        mirrored_doc_type = mirrored.doc_type
        session.delete(mirrored)
        session.flush()
        if check is not None:
            reindex_documents_for_doc_types(check, [mirrored_doc_type])

    session.delete(doc)
    session.commit()
    return {"ok": True}
