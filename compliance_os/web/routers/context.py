"""Receive a user's exported data room for a named purpose, for future services."""
from __future__ import annotations

import re
import uuid
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
