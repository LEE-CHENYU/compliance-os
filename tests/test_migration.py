"""Tests for migration.py, mcp_install local-mode, and version bump."""
import io
import json
import os
import zipfile
from pathlib import Path

import pytest


def test_mcp_server_config_is_local_mode():
    from compliance_os.mcp_install import _mcp_server_config

    cfg = _mcp_server_config("gdn_oc_aa_bb")
    assert cfg["env"] == {"GUARDIAN_LICENSE_KEY": "gdn_oc_aa_bb", "GUARDIAN_MODE": "local"}
    assert cfg["args"] == ["-m", "compliance_os.mcp_server"]


def test_write_toml_config_writes_local_env(tmp_path):
    from compliance_os.mcp_install import _write_toml_config

    path = tmp_path / "config.toml"
    _write_toml_config(path, "gdn_oc_cc_dd")
    text = path.read_text()
    assert 'GUARDIAN_LICENSE_KEY = "gdn_oc_cc_dd"' in text
    assert 'GUARDIAN_MODE = "local"' in text
    assert "GUARDIAN_API_URL" not in text


def _make_source_db(tmp_path):
    """A standalone 'hosted-style' DB with one user + check + doc(file) + facts."""
    import secrets
    from sqlalchemy.orm import sessionmaker
    from compliance_os.web.models.database import create_engine_and_tables
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.models.tables_v2 import (
        CheckRow, DocumentRow, ExtractedFieldRow, UserFactRow,
    )

    engine = create_engine_and_tables(db_path=str(tmp_path / "source.db"))
    db = sessionmaker(bind=engine)()

    user = UserRow(email=f"src{secrets.token_hex(3)}@x.com", password_hash="x", role="user")
    db.add(user); db.flush()
    check = CheckRow(track="stem_opt", status="saved", user_id=user.id, answers={})
    db.add(check); db.flush()

    # a real upload file on disk
    updir = tmp_path / "src_uploads" / check.id
    updir.mkdir(parents=True)
    fpath = updir / "i20.txt"
    fpath.write_text("SEVIS ID: N0001234567")

    doc = DocumentRow(
        check_id=check.id, doc_type="i20", filename="i20.txt",
        file_path=str(fpath), file_size=fpath.stat().st_size,
        mime_type="text/plain", ocr_text="SEVIS ID: N0001234567",
    )
    db.add(doc); db.flush()
    db.add(ExtractedFieldRow(document_id=doc.id, field_name="sevis_number",
                             field_value="N0001234567", confidence=0.95))
    db.add(UserFactRow(user_id=user.id, fact_key="sevis_id", label="SEVIS ID",
                       category="immigration", track="student",
                       value={"v": "N0001234567"}, source_type="document",
                       is_active=True))
    db.commit()
    return db, user.id


def test_export_user_data_produces_zip(tmp_path):
    from compliance_os import migration

    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id)
    db.close()

    zf = zipfile.ZipFile(io.BytesIO(blob))
    names = set(zf.namelist())
    assert "data.json" in names
    assert any(n.startswith("uploads/") and n.endswith("i20.txt") for n in names)

    data = json.loads(zf.read("data.json"))
    assert len(data["checks"]) == 1
    assert len(data["documents"]) == 1
    assert len(data["extracted_fields"]) == 1
    assert len(data["user_facts"]) == 1
    assert data["user_facts"][0]["fact_key"] == "sevis_id"


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield tmp_path
    database._engine = None
    database._SessionLocal = None


def test_import_lands_data_under_local_user(local_env, tmp_path):
    from compliance_os import migration
    from compliance_os.web.models import database
    from compliance_os.web.models.tables_v2 import DocumentRow, UserFactRow
    from compliance_os import local_engine

    # Build an export from a standalone source DB.
    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id)
    db.close()
    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(blob)

    summary = migration.import_data(str(zip_path))
    assert summary["checks"] == 1 and summary["documents"] == 1 and summary["user_facts"] == 1

    ldb = next(database.get_session())
    try:
        local_uid = local_engine.get_local_user_id(ldb)
        facts = ldb.query(UserFactRow).filter(UserFactRow.user_id == local_uid).all()
        assert any(f.fact_key == "sevis_id" for f in facts)
        doc = ldb.query(DocumentRow).first()
        # file rebased under the local home and actually copied
        assert str(tmp_path / "home") in doc.file_path
        assert Path(doc.file_path).exists()
        assert Path(doc.file_path).read_text() == "SEVIS ID: N0001234567"
    finally:
        ldb.close()
