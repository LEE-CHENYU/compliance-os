"""Dashboard API — timeline, stats, upload, documents."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.auth_service import decode_token
from compliance_os.web.services.extractor import extract_document, extract_pdf_text
from compliance_os.web.services.timeline_builder import build_stats, build_timeline

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads"

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing authorization")
    payload = decode_token(authorization.split(" ", 1)[1])
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.get("/timeline")
def get_timeline(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    return build_timeline(user.id, db)


@router.get("/stats")
def get_stats(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    return build_stats(user.id, db)


@router.get("/documents")
def list_documents(
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    checks = db.query(CheckRow).filter(CheckRow.user_id == user.id).all()
    docs = []
    for check in checks:
        for doc in check.documents:
            docs.append({
                "id": doc.id,
                "filename": doc.filename,
                "doc_type": doc.doc_type,
                "file_size": doc.file_size,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            })
    return docs


@router.post("/upload")
def upload_to_dataroom(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Upload a document to the data room. Auto-extracts and re-evaluates."""
    user = _get_user(authorization, db)

    # Find or create a check to attach this document to
    check = db.query(CheckRow).filter(
        CheckRow.user_id == user.id,
        CheckRow.status == "saved",
    ).first()

    if not check:
        check = CheckRow(track="stem_opt", status="saved", user_id=user.id, answers={})
        db.add(check)
        db.flush()

    # Save file
    upload_dir = UPLOAD_DIR / check.id
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / filename
    content = file.file.read()
    file_path.write_bytes(content)

    # Create document record
    doc = DocumentRow(
        check_id=check.id,
        doc_type=doc_type,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Auto-extract
    try:
        text = extract_pdf_text(str(file_path))
        fields = extract_document(doc_type, text)
        for field_name, data in fields.items():
            row = ExtractedFieldRow(
                document_id=doc.id,
                field_name=field_name,
                field_value=str(data["value"]) if data["value"] is not None else None,
                confidence=data.get("confidence"),
            )
            db.add(row)
        db.commit()
    except Exception:
        pass  # Extraction failure is non-fatal for data room uploads

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

    return {"ok": True, "document_id": doc.id}
