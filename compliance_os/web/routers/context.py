"""Receive a user's exported data room for a named purpose, for future services."""
from __future__ import annotations

import io
import os
import re
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import DATA_DIR, get_session
from compliance_os.web.models.tables_v2 import SharedContextRow
from compliance_os.web.services.auth_service import get_bearer_payload

router = APIRouter(prefix="/api/context", tags=["context"])

SHARED_DIR = DATA_DIR / "shared_context"
MAX_SHARE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_EXTRACT_BYTES = 300 * 1024 * 1024  # uncompressed cap for published data rooms
MAX_EXTRACT_MEMBERS = 2000


def _public_url() -> str:
    return os.environ.get("GUARDIAN_PUBLIC_URL", "https://guardiancompliance.app").rstrip("/")


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.post("/share")
async def share_context(
    purpose: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", purpose):
        raise HTTPException(400, "Invalid purpose: use letters, digits, hyphen, underscore (max 64).")
    content = await file.read()
    if len(content) > MAX_SHARE_BYTES:
        raise HTTPException(413, "Upload too large.")
    user_dir = SHARED_DIR / user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    ref = str(uuid.uuid4())
    dest = user_dir / f"{purpose}-{ref}.zip"
    if not str(dest.resolve()).startswith(str(user_dir.resolve()) + "/"):
        raise HTTPException(400, "Invalid purpose path.")
    dest.write_bytes(content)
    row = SharedContextRow(id=ref, user_id=user.id, purpose=purpose, path=str(dest))
    db.add(row)
    db.commit()
    return {"reference_id": ref, "purpose": purpose, "stored_at": str(dest)}


def _safe_extract_zip(content: bytes, extract_dir: Path) -> int:
    """Extract a zip with zip-slip protection and size/member caps.
    Returns the number of files written."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Upload is not a valid zip archive.")
    with zf:
        members = zf.infolist()
        if len(members) > MAX_EXTRACT_MEMBERS:
            raise HTTPException(413, "Archive has too many files.")
        if sum(m.file_size for m in members) > MAX_EXTRACT_BYTES:
            raise HTTPException(413, "Archive too large when extracted.")
        extract_root = extract_dir.resolve()
        written = 0
        for m in members:
            if m.is_dir():
                continue
            target = (extract_dir / m.filename).resolve()
            if not str(target).startswith(str(extract_root) + os.sep):
                raise HTTPException(400, "Archive contains an unsafe path.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(m) as src:
                target.write_bytes(src.read())
            written += 1
    return written


@router.post("/publish-dataroom")
async def publish_dataroom(
    template_id: str = Form("h1b_petition"),
    recipient: str = Form(""),
    expires_in_days: int = Form(14),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    """Receive a user's data-room zip, extract it server-side, and mint a
    read-only share link rendered by the existing /share/[token] web page."""
    from compliance_os.case_templates import TEMPLATES
    from compliance_os.web.services.share_tokens import create_share_token

    user = _get_user(authorization, db)
    tpl_key = (template_id or "").strip().lower()
    if tpl_key not in TEMPLATES:
        raise HTTPException(
            400, f"Unknown template '{template_id}'. Available: {sorted(TEMPLATES)}"
        )
    days = max(1, min(int(expires_in_days or 14), 90))
    content = await file.read()
    if len(content) > MAX_SHARE_BYTES:
        raise HTTPException(413, "Upload too large.")

    user_dir = SHARED_DIR / user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    ref = str(uuid.uuid4())
    (user_dir / f"dataroom-{ref}.zip").write_bytes(content)
    extract_dir = user_dir / f"dataroom-{ref}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    files_written = _safe_extract_zip(content, extract_dir)

    token = create_share_token(
        folder=str(extract_dir),
        template_id=tpl_key,
        recipient=recipient,
        issuer=user.email or user.id,
        expires_in_days=days,
    )
    row = SharedContextRow(
        id=ref, user_id=user.id, purpose="dataroom-view",
        path=str(user_dir / f"dataroom-{ref}.zip"),
    )
    db.add(row)
    db.commit()
    return {
        "reference_id": ref,
        "url": f"{_public_url()}/share/{token}",
        "token": token,
        "template_id": tpl_key,
        "expires_in_days": days,
        "files": files_written,
    }
