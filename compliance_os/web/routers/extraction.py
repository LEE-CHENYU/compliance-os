"""Document upload, LLM extraction, extraction results."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.database import get_session
from compliance_os.web.models.schemas_v2 import DocumentOut, ExtractedField
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.extractor import extract_document, extract_pdf_text

UPLOAD_DIR = Path(__file__).parents[3] / "uploads"

router = APIRouter(prefix="/api/checks/{check_id}", tags=["extraction"])


@router.post("/documents", response_model=DocumentOut)
def upload_document(
    check_id: str,
    doc_type: str = Form(...),
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
    file_path.write_bytes(content)

    row = DocumentRow(
        check_id=check_id,
        doc_type=doc_type,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(row)
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

    results = {}
    for doc in check.documents:
        text = extract_pdf_text(doc.file_path)
        fields = extract_document(doc.doc_type, text)

        # Clear old extractions for this doc
        for old in doc.extracted_fields:
            db.delete(old)

        for field_name, data in fields.items():
            row = ExtractedFieldRow(
                document_id=doc.id,
                field_name=field_name,
                field_value=str(data["value"]) if data["value"] is not None else None,
                confidence=data.get("confidence"),
            )
            db.add(row)

        results[doc.doc_type] = {k: v["value"] for k, v in fields.items()}

    check.status = "extracted"
    db.commit()
    return {"status": "extracted", "results": results}


@router.get("/extractions", response_model=dict[str, list[ExtractedField]])
def get_extractions(check_id: str, db: Session = Depends(get_session)):
    check = db.get(CheckRow, check_id)
    if not check:
        raise HTTPException(404, "Check not found")

    result: dict[str, list] = {}
    for doc in check.documents:
        result[doc.doc_type] = doc.extracted_fields
    return result
