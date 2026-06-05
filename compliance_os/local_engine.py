# compliance_os/local_engine.py
"""In-process local engine for the Guardian MCP extension.

When GUARDIAN_MODE=local, the MCP tools call these adapters instead of
proxying to the hosted Guardian API. Everything runs against the local
SQLite SoT at ~/.guardian/guardian.db using the already transport-
agnostic service layer in compliance_os.web.services.*.
"""
from __future__ import annotations

import os
import secrets

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.services.user_facts import (
    get_active_facts,
    resolve_conflict,
    serialize_fact,
    upsert_fact,
)

LOCAL_USER_EMAIL = "local@guardian.local"


def is_local_mode() -> bool:
    """True when the extension should run fully in-process (no hosted API)."""
    return (os.environ.get("GUARDIAN_MODE") or "").strip().lower() == "local"


def get_local_user_id(db) -> str:
    """Return the singleton local user's id, creating it on first use.

    Local mode is single-user (whoever installed the extension), so there
    is no auth — we only need a stable user_id to scope SoT rows. The
    password_hash is random and never used for login.
    """
    user = (
        db.query(UserRow)
        .filter(UserRow.email == LOCAL_USER_EMAIL)
        .one_or_none()
    )
    if user is None:
        user = UserRow(
            email=LOCAL_USER_EMAIL,
            password_hash=secrets.token_hex(16),
            role="user",
        )
        db.add(user)
        db.commit()
    return user.id


def local_get_facts(category: str = "", track: str = "") -> dict:
    """In-process equivalent of GET /api/facts → {"facts": [...]}."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        rows = get_active_facts(
            db, user_id=user_id,
            category=category or None, track=track or None,
        )
        return {"facts": [serialize_fact(r) for r in rows]}
    finally:
        db.close()


def local_set_fact(
    fact_key: str, value: str, notes: str = "", label: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts (a user-locked decision)."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        new_row, superseded = upsert_fact(
            db, user_id=user_id, fact_key=fact_key, value=value,
            source_type="decision_lock",
            source_ref={"ui_path": "mcp:set_user_fact"},
            notes=notes or None, label=label or None,
        )
        db.commit()
        return {
            "fact": serialize_fact(new_row),
            "superseded": serialize_fact(superseded) if superseded else None,
        }
    finally:
        db.close()


def local_resolve_conflict(
    fact_id: str, choice: str, user_value: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts/{fact_id}/resolve."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        row = resolve_conflict(
            db, user_id=user_id, fact_id=fact_id,
            choice=choice, user_value=user_value or None,
        )
        db.commit()
        return {"fact": serialize_fact(row)}
    finally:
        db.close()


def force_local_embeddings() -> None:
    """Pin embeddings to the local provider so no OpenAI key is ever used
    in local mode (privacy + $0 cost). Idempotent."""
    os.environ["GUARDIAN_EMBEDDING_PROVIDER"] = "local"


def _get_local_check(db, user_id: str):
    """Find-or-create the singleton local 'check' that documents attach to.

    Mirrors dashboard._ensure_dashboard_check, replicated here so the
    local engine doesn't import the FastAPI router. One saved check per
    local user is enough for single-user local mode.
    """
    from compliance_os.web.models.tables_v2 import CheckRow

    check = (
        db.query(CheckRow)
        .filter(CheckRow.user_id == user_id, CheckRow.status == "saved")
        .first()
    )
    if check is None:
        check = CheckRow(track="stem_opt", status="saved", user_id=user_id, answers={})
        db.add(check)
        db.flush()
    return check


def _local_ocr_text(path) -> str:
    """Extract document text locally (no API). PDF→PyMuPDF, DOCX→python-docx,
    everything else→plain read. Returns "" on ANY failure so a corrupt file
    never propagates an unhandled exception through local_upload_document
    (which would skip the ocr_text commit and break the {"error": ...} contract)."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            from compliance_os.web.services.extractor import extract_pdf_text_with_provenance

            return extract_pdf_text_with_provenance(str(path)).text or ""
        if suffix in {".docx", ".doc"}:
            from compliance_os.web.services.docx_reader import extract_text

            return extract_text(str(path)) or ""
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def local_upload_document(file_path: str, doc_type: str = "") -> dict:
    """Store a document into the local data room WITHOUT extracting facts.

    Deterministic + in-process: classify (if needed), copy the file under
    ~/.guardian/uploads/<check_id>/, create the DocumentRow, run versioning
    (register_uploaded_document), and read the text locally. Returns the
    doc_id, the parsed text, and the extraction schema so the caller's
    Claude can read the field values and submit record_extracted_facts.
    No server LLM, no HTTP.
    """
    import mimetypes
    import uuid as _uuid
    from pathlib import Path

    from compliance_os.facts.extraction_map import schema_for_doc_type
    from compliance_os.web.models.tables_v2 import DocumentRow
    from compliance_os.web.services.classifier import classify_file
    from compliance_os.web.services.document_store import register_uploaded_document

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    content = path.read_bytes()
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if not doc_type:
        doc_type = classify_file(str(path), mime_type, allow_ocr=False).doc_type or "unknown"

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        check = _get_local_check(db, user_id)
        # Resolve the uploads root from env LIVE (not settings, which is a
        # frozen singleton) so it honors GUARDIAN_HOME/GUARDIAN_DATA_DIR the
        # same way database.py resolves the DB path.
        guardian_home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
        upload_root = Path(os.environ.get("GUARDIAN_DATA_DIR") or (guardian_home / "uploads"))
        upload_dir = upload_root / check.id
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / f"{_uuid.uuid4()}_{path.name}"
        dest.write_bytes(content)

        doc = DocumentRow(
            check_id=check.id,
            doc_type=doc_type,
            filename=path.name,
            file_path=str(dest),
            file_size=len(content),
            mime_type=mime_type,
            provenance={"classification": {"doc_type": doc_type, "source": "local_upload"}},
        )
        db.add(doc)
        db.flush()
        register_uploaded_document(check, doc, content, source_path=None, db=db)
        db.commit()
        db.refresh(doc)

        text = _local_ocr_text(dest)
        doc.ocr_text = text
        db.commit()

        return {
            "doc_id": doc.id,
            "doc_type": doc.doc_type,
            "text": text[:50_000],
            "extraction_schema": schema_for_doc_type(doc.doc_type),
        }
    finally:
        db.close()


def local_record_extracted_facts(doc_id: str, facts: list) -> dict:
    """Project Claude-extracted fields into the SoT for a stored document.

    `facts` is a list of {"field_name": <raw extractor field>, "value": str,
    "confidence": float (optional, default 1.0), "raw_text": str (optional)}.
    Each is written as an ExtractedFieldRow and — when it maps to a canonical
    fact_key and clears the confidence bar — projected into user_facts with
    supersession + conflict detection, reusing the deterministic
    _upsert_extracted_field path (no LLM). Returns the recorded field names,
    the resulting active facts, and any detected conflicts.
    """
    from compliance_os.web.models.tables_v2 import DocumentRow
    from compliance_os.web.services.document_store import _upsert_extracted_field

    db = next(get_session())
    try:
        doc = db.get(DocumentRow, doc_id)
        if doc is None:
            return {"error": f"document not found: {doc_id}"}

        recorded: list[str] = []
        for f in facts:
            field_name = f.get("field_name") or f.get("source_field")
            if not field_name:
                continue
            value = f.get("value")
            _upsert_extracted_field(
                db,
                doc=doc,
                field_name=field_name,
                value=str(value) if value is not None else None,
                confidence=f.get("confidence", 1.0),
                raw_text=f.get("raw_text"),
            )
            recorded.append(field_name)
        db.commit()

        user_id = get_local_user_id(db)
        rows = get_active_facts(db, user_id=user_id)
        return {
            "recorded_fields": recorded,
            "facts": [serialize_fact(r) for r in rows],
            "conflicts": [serialize_fact(r) for r in rows if r.detected_conflicts],
        }
    finally:
        db.close()


def local_ask_grounding(question: str) -> dict:
    """Gather local grounding for a question — chunks + facts — with NO model.

    Returns the retrieved document context and references so the caller's
    Claude composes the answer itself. This replaces the server-side
    RAG+LLM `guardian_ask` in local mode: retrieval stays local, the
    answer moves to the user's Claude.
    """
    # Direct import from the chat router is verified safe in local mode:
    # chat_completion (the only LLM dependency) is imported lazily inside the
    # endpoint, so loading this module triggers no model/key side effects. If
    # that ever changes, extract _build_context into a service module.
    from compliance_os.web.routers.chat import _build_context

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        context_text, references = _build_context(user_id, db, query=question)
        return {
            "question": question,
            "context": context_text,
            "references": references,
        }
    finally:
        db.close()
