"""Hosted→local data migration for Guardian.

export_user_data(db, user_id) zips a user's data room + facts SoT (the
deterministic tables plus the on-disk upload files). import_data(zip) loads
it into the local ~/.guardian/guardian.db, keeping original row IDs (so all
FKs survive) and remapping only user_id to the local singleton user. Both
sides share the generic row (de)serialization below.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime
from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import (
    CheckRow,
    DocumentRow,
    ExtractedFieldRow,
    UserFactRow,
)

EXPORT_VERSION = 1


def _row_to_dict(row) -> dict:
    """Serialize an ORM row to a JSON-safe dict (datetimes → ISO strings)."""
    out: dict = {}
    for col in row.__table__.columns:
        value = getattr(row, col.key)
        if isinstance(value, datetime):
            value = value.isoformat()
        out[col.key] = value
    return out


def _kwargs_from_dict(model, data: dict, overrides: dict | None = None) -> dict:
    """Build constructor kwargs for `model` from a serialized dict, parsing
    DateTime columns back from ISO strings and dropping unknown keys."""
    cols = {c.key: c for c in model.__table__.columns}
    kwargs: dict = {}
    for key, value in data.items():
        col = cols.get(key)
        if col is None:
            continue
        if isinstance(col.type, DateTime) and isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                value = None
        kwargs[key] = value
    if overrides:
        kwargs.update(overrides)
    return kwargs


def export_user_data(db: Session, user_id: str) -> bytes:
    """Return a zip (bytes) of the user's checks, documents, extracted fields,
    user_facts, and the on-disk upload files."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()
    check_ids = [c.id for c in checks]
    documents = (
        db.query(DocumentRow).filter(DocumentRow.check_id.in_(check_ids)).all()
        if check_ids else []
    )
    doc_ids = [d.id for d in documents]
    fields = (
        db.query(ExtractedFieldRow)
        .filter(ExtractedFieldRow.document_id.in_(doc_ids)).all()
        if doc_ids else []
    )
    facts = db.query(UserFactRow).filter(UserFactRow.user_id == user_id).all()

    data = {
        "export_version": EXPORT_VERSION,
        "checks": [_row_to_dict(c) for c in checks],
        "documents": [_row_to_dict(d) for d in documents],
        "extracted_fields": [_row_to_dict(f) for f in fields],
        "user_facts": [_row_to_dict(f) for f in facts],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(data, indent=2, default=str))
        for d in documents:
            src = Path(d.file_path) if d.file_path else None
            if src and src.exists():
                # canonical relative path the importer rebases from
                zf.write(src, f"uploads/{d.check_id}/{src.name}")
    return buf.getvalue()


def _uploads_root() -> Path:
    import os

    home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
    return Path(os.environ.get("GUARDIAN_DATA_DIR") or (home / "uploads"))


def import_data(zip_path: str) -> dict:
    """Load an export zip into the local ~/.guardian/guardian.db.

    Keeps original row IDs (preserving FKs) and remaps user_id to the local
    singleton user. Rebases each document's file_path under the local uploads
    root and copies the bundled file. Skips rows whose id already exists, so
    re-import is safe. Returns a count summary.
    """
    import os

    os.environ["GUARDIAN_MODE"] = "local"
    from compliance_os.web.models import database

    database._engine = None
    database._SessionLocal = None

    from compliance_os.local_engine import get_local_user_id

    counts = {"checks": 0, "documents": 0, "extracted_fields": 0, "user_facts": 0}
    uploads_root = _uploads_root()

    with zipfile.ZipFile(zip_path) as zf:
        data = json.loads(zf.read("data.json"))

        db = next(database.get_session())
        try:
            local_uid = get_local_user_id(db)

            for c in data.get("checks", []):
                if db.get(CheckRow, c["id"]) is not None:
                    continue
                db.add(CheckRow(**_kwargs_from_dict(CheckRow, c, {"user_id": local_uid})))
                counts["checks"] += 1

            for d in data.get("documents", []):
                if db.get(DocumentRow, d["id"]) is not None:
                    continue
                src_name = Path(d["file_path"]).name if d.get("file_path") else None
                new_path = d.get("file_path")
                if src_name:
                    dest_dir = uploads_root / d["check_id"]
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / src_name
                    arc = f"uploads/{d['check_id']}/{src_name}"
                    try:
                        dest.write_bytes(zf.read(arc))
                    except KeyError:
                        pass  # file missing from the export — keep the row, rebased path
                    new_path = str(dest)
                db.add(DocumentRow(**_kwargs_from_dict(DocumentRow, d, {"file_path": new_path})))
                counts["documents"] += 1

            for f in data.get("extracted_fields", []):
                if db.get(ExtractedFieldRow, f["id"]) is not None:
                    continue
                db.add(ExtractedFieldRow(**_kwargs_from_dict(ExtractedFieldRow, f)))
                counts["extracted_fields"] += 1

            for f in data.get("user_facts", []):
                if db.get(UserFactRow, f["id"]) is not None:
                    continue
                db.add(UserFactRow(**_kwargs_from_dict(UserFactRow, f, {"user_id": local_uid})))
                counts["user_facts"] += 1

            db.commit()
        finally:
            db.close()

    return counts
