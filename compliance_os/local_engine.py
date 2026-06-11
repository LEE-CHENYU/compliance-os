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
    from compliance_os.cascade import cascade_after_write, crosscheck_keys

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        before_cc = crosscheck_keys(db, user_id)
        existed_before = any(
            r.fact_key == fact_key for r in get_active_facts(db, user_id=user_id)
        )
        new_row, superseded = upsert_fact(
            db, user_id=user_id, fact_key=fact_key, value=value,
            source_type="decision_lock",
            source_ref={"ui_path": "mcp:set_user_fact"},
            notes=notes or None, label=label or None,
        )
        db.commit()
        # Only cascade on a real change (new fact or changed value), not an
        # idempotent re-set — mirrors the document path's diff-based behavior.
        changed = (superseded is not None) or (not existed_before)
        cascade = cascade_after_write(
            db, user_id, [new_row.fact_key] if changed else [], before_cc
        )
        return {
            "fact": serialize_fact(new_row),
            "superseded": serialize_fact(superseded) if superseded else None,
            "cascade": cascade,
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


def local_uploads_root():
    """The on-device uploads root in local mode: GUARDIAN_DATA_DIR, else
    GUARDIAN_HOME/uploads. Resolved from env LIVE (not the frozen settings
    singleton). Documents land under <root>/<check_id>/. Shared by
    local_upload_document and the index/query tools so the vector index
    points at the same place the data room writes to."""
    from pathlib import Path

    guardian_home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
    return Path(os.environ.get("GUARDIAN_DATA_DIR") or (guardian_home / "uploads"))


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
        # Uploads root resolved from env LIVE (shared with the index/query
        # tools via local_uploads_root) so the vector index scans the same
        # place the data room writes to.
        upload_dir = local_uploads_root() / check.id
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

        # Actively maintain the canonical data-room mirror (copy, never move).
        # Best-effort: a sync failure must never break the upload contract.
        try:
            from compliance_os.dataroom import sync_data_room
            data_room = sync_data_room(db, user_id)
        except Exception:
            data_room = None

        return {
            "doc_id": doc.id,
            "doc_type": doc.doc_type,
            "text": text[:50_000],
            "extraction_schema": schema_for_doc_type(doc.doc_type),
            "data_room": data_room,
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

    def _unwrap(v):
        return v["v"] if isinstance(v, dict) and "v" in v else v

    db = next(get_session())
    try:
        doc = db.get(DocumentRow, doc_id)
        if doc is None:
            return {"error": f"document not found: {doc_id}"}

        from compliance_os.cascade import cascade_after_write, crosscheck_keys

        user_id = get_local_user_id(db)
        # Snapshot canonical facts BEFORE recording so we can report a precise
        # before→after diff (the wedge) without threading deltas through the
        # document_store projection. Also snapshot the cross-check findings so
        # the cascade can report only what THIS document newly triggered.
        before = {
            r.fact_key: {"value": _unwrap(r.value), "label": r.label}
            for r in get_active_facts(db, user_id=user_id)
        }
        before_cc = crosscheck_keys(db, user_id)

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

        rows = get_active_facts(db, user_id=user_id)
        changes = []
        for r in rows:
            new_v = _unwrap(r.value)
            prior = before.get(r.fact_key)
            if prior is None:
                changes.append({"fact_key": r.fact_key, "label": r.label,
                                "old": None, "new": new_v})
            elif prior["value"] != new_v:
                changes.append({"fact_key": r.fact_key, "label": r.label,
                                "old": prior["value"], "new": new_v})
        cascade = cascade_after_write(
            db, user_id, [c["fact_key"] for c in changes], before_cc
        )
        # Refresh the canonical mirror so manifest.json / INDEX.md pick up the
        # newly recorded file→data mapping. Best-effort.
        try:
            from compliance_os.dataroom import sync_data_room
            data_room = sync_data_room(db, user_id)
        except Exception:
            data_room = None
        return {
            "recorded_fields": recorded,
            "changes": changes,
            "cascade": cascade,
            "data_room": data_room,
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


def local_cross_check(chain: str = "") -> dict:
    """Run the chain-aware cross-check over the local data room."""
    from compliance_os.compliance.cross_check import cross_check

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        return cross_check(db, user_id, chain=chain or None)
    finally:
        db.close()


GUARDIAN_CLOUD_URL = os.environ.get("GUARDIAN_CLOUD_URL", "https://guardian-compliance.fly.dev")

_SHARE_DATA_CATEGORIES = ["sot_facts", "documents"]


def _resolve_license_token() -> str:
    """The license key is the bearer token for cloud egress."""
    return os.environ.get("GUARDIAN_LICENSE_KEY", "")


def _post_context_share(zip_bytes: bytes, purpose: str, token: str) -> dict:
    """POST the export zip to the cloud context-share endpoint. Real network."""
    import json
    import uuid
    from urllib import error, request

    boundary = uuid.uuid4().hex
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\n{purpose}\r\n".encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"data_room.zip\"\r\nContent-Type: application/zip\r\n\r\n".encode()
    )
    parts.append(zip_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{GUARDIAN_CLOUD_URL}/api/context/share", data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
    except error.HTTPError as exc:
        raise RuntimeError(f"context/share failed ({exc.code}): {exc.read().decode()[:200]}") from exc
    except (error.URLError, ValueError) as exc:
        raise RuntimeError(f"context/share failed: {exc}") from exc
    if not payload.get("reference_id"):
        raise RuntimeError(f"context/share returned no reference_id: {payload}")
    return payload


def local_share_data_room(purpose: str, confirm: bool = False, remember: str = "once") -> dict:
    """Consent-gated upload of the local SoT + documents to Guardian cloud."""
    from compliance_os import consent
    from compliance_os.migration import export_user_data

    def _do_share() -> dict:
        db = next(get_session())
        try:
            user_id = get_local_user_id(db)
            zip_bytes = export_user_data(db, user_id)
        finally:
            db.close()
        result = _post_context_share(zip_bytes, purpose, _resolve_license_token())
        return {"status": "shared", "purpose": purpose,
                "reference_id": result.get("reference_id"),
                "message": f"Shared your data room for '{purpose}'."}

    if consent.has_consent(purpose):
        return _do_share()
    if not confirm:
        return {
            "status": "consent_required",
            "purpose": purpose,
            "destination": "Guardian cloud",
            "data_categories": _SHARE_DATA_CATEGORIES,
            "message": (
                f"This will upload your facts source-of-truth and your documents to "
                f"Guardian's cloud for '{purpose}'. Nothing is sent unless you approve. "
                f"To proceed, call again with confirm=true and remember set to "
                f"'once', 'session', or 'always'. To decline, do nothing."
            ),
        }
    consent.record_consent(purpose, remember, destination="guardian_cloud",
                           data_categories=_SHARE_DATA_CATEGORIES)
    return _do_share()


def local_build_data_room() -> dict:
    """Run the canonical data-room sync (copy-mirror + manifest) on demand."""
    from compliance_os.dataroom import sync_data_room

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        return sync_data_room(db, user_id)
    finally:
        db.close()


def _zip_dir(root) -> bytes:
    """Zip a directory tree (paths relative to root) into bytes."""
    import io
    import zipfile
    from pathlib import Path

    root = Path(root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(root).as_posix())
    return buf.getvalue()


def _post_publish_dataroom(
    zip_bytes: bytes, template_id: str, recipient: str,
    expires_in_days: int, token: str,
) -> dict:
    """POST the data-room zip to the cloud publish endpoint; returns the
    share URL payload. Real network."""
    import json
    import uuid
    from urllib import error, request

    boundary = uuid.uuid4().hex
    fields = {
        "template_id": template_id,
        "recipient": recipient,
        "expires_in_days": str(expires_in_days),
    }
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f"name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"data_room.zip\"\r\nContent-Type: application/zip\r\n\r\n".encode()
    )
    parts.append(zip_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(
        f"{GUARDIAN_CLOUD_URL}/api/context/publish-dataroom",
        data=body, headers=headers, method="POST",
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
    except error.HTTPError as exc:
        raise RuntimeError(f"publish-dataroom failed ({exc.code}): {exc.read().decode()[:200]}") from exc
    except (error.URLError, ValueError) as exc:
        raise RuntimeError(f"publish-dataroom failed: {exc}") from exc
    if not payload.get("url"):
        raise RuntimeError(f"publish-dataroom returned no url: {payload}")
    return payload


def local_publish_data_room(
    template_id: str = "h1b_petition", recipient: str = "",
    expires_in_days: int = 14, confirm: bool = False, remember: str = "once",
) -> dict:
    """Consent-gated: sync the canonical data room, upload it to Guardian
    cloud, and get back a private share URL rendered by the existing web
    data-room template. Same consent discipline as share_data_room."""
    from compliance_os import consent
    from compliance_os.dataroom import dataroom_root, sync_data_room

    purpose = "dataroom-view"

    def _do_publish() -> dict:
        db = next(get_session())
        try:
            user_id = get_local_user_id(db)
            summary = sync_data_room(db, user_id)
        finally:
            db.close()
        zip_bytes = _zip_dir(dataroom_root())
        result = _post_publish_dataroom(
            zip_bytes, template_id, recipient,
            expires_in_days, _resolve_license_token(),
        )
        return {
            "status": "published",
            "url": result.get("url"),
            "reference_id": result.get("reference_id"),
            "expires_in_days": result.get("expires_in_days", expires_in_days),
            "files": summary.get("total"),
            "template_id": template_id,
        }

    if consent.has_consent(purpose):
        return _do_publish()
    if not confirm:
        return {
            "status": "consent_required",
            "purpose": purpose,
            "destination": "Guardian cloud",
            "data_categories": _SHARE_DATA_CATEGORIES,
            "message": (
                "This will upload your data room (documents + facts manifest) to "
                "Guardian's cloud and create a private share link rendered at "
                "guardiancompliance.app. Nothing is sent unless you approve. To "
                "proceed, call again with confirm=true and remember set to "
                "'once', 'session', or 'always'. To decline, do nothing."
            ),
        }
    consent.record_consent(purpose, remember, destination="guardian_cloud",
                           data_categories=_SHARE_DATA_CATEGORIES)
    return _do_publish()
