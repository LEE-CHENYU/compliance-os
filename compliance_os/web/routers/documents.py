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
from compliance_os.web.models.tables import CaseRow, DiscoveryAnswerRow, DocumentRow
from compliance_os.web.services.checklist import generate_checklist
from compliance_os.web.services.classifier import classify_file

UPLOADS_DIR = Path(__file__).parents[3] / "uploads"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/csv", "text/plain"}

router = APIRouter(prefix="/api/cases/{case_id}/documents", tags=["documents"])


def _get_case(case_id: str, session: Session) -> CaseRow:
    case = session.get(CaseRow, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _doc_response(d: DocumentRow) -> DocumentResponse:
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
    docs = session.query(DocumentRow).filter_by(case_id=case_id).all()
    filled = {d.slot_key: d.id for d in docs if d.slot_key}
    return DocumentChecklistResponse(slots=slots, filled=filled)


@router.post("", response_model=DocumentResponse)
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    slot_key: str | None = Form(None),
    session: Session = Depends(get_session),
):
    _get_case(case_id, session)

    # Validate type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 20MB limit")

    # Save file
    case_dir = UPLOADS_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_name = file.filename or "upload"
    dest = case_dir / f"{file_id}_{safe_name}"
    dest.write_bytes(content)

    # Classify
    classification_result = classify_file(str(dest), file.content_type or "")

    # Create record
    doc = DocumentRow(
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
    docs = session.query(DocumentRow).filter_by(case_id=case_id).order_by(DocumentRow.uploaded_at).all()
    return DocumentListResponse(documents=[_doc_response(d) for d in docs])


@router.patch("/{doc_id}", response_model=DocumentResponse)
def update_document(case_id: str, doc_id: str, body: DocumentUpdateRequest, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    doc = session.get(DocumentRow, doc_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    if body.slot_key is not None:
        doc.slot_key = body.slot_key
    if body.classification is not None:
        doc.classification = body.classification
    session.commit()
    session.refresh(doc)
    return _doc_response(doc)


@router.delete("/{doc_id}")
def delete_document(case_id: str, doc_id: str, session: Session = Depends(get_session)):
    _get_case(case_id, session)
    doc = session.get(DocumentRow, doc_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    # Delete file
    try:
        os.remove(doc.file_path)
    except OSError:
        pass
    session.delete(doc)
    session.commit()
    return {"ok": True}
