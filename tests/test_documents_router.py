"""Test document upload and management API endpoints."""

import pytest

import compliance_os.web.routers.documents as doc_mod
from compliance_os.web.services.document_intake import ResolvedDocumentType


@pytest.fixture
def client(tmp_path):
    """Override client to also patch uploads dir."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from compliance_os.web.app import app
    from compliance_os.web.models import database

    db_path = str(tmp_path / "test.db")
    database._engine = None
    database._SessionLocal = None
    engine = database.create_engine_and_tables(db_path)
    database._engine = engine
    database._SessionLocal = sessionmaker(bind=engine)

    original_uploads = doc_mod.UPLOADS_DIR
    doc_mod.UPLOADS_DIR = tmp_path / "uploads"
    yield TestClient(app)
    doc_mod.UPLOADS_DIR = original_uploads
    database._engine = None
    database._SessionLocal = None


@pytest.fixture
def case_id(client):
    resp = client.post("/api/cases", json={"workflow_type": "tax"})
    return resp.json()["id"]


def test_upload_document(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test.txt"
    assert data["file_size"] == 11
    assert data["status"] == "uploaded"


def test_upload_document_uses_fast_classification(client, case_id, monkeypatch):
    calls: list[tuple[str, str, bool]] = []

    def fake_resolve(file_path: str, mime_type: str, *, provided_doc_type=None, allow_ocr: bool = True):
        calls.append((file_path, mime_type, allow_ocr))
        return ResolvedDocumentType(doc_type="lease", confidence="high", source="filename")

    monkeypatch.setattr(doc_mod, "resolve_document_type", fake_resolve)

    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("sublease agreement.pdf", b"fake pdf", "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["classification"] == "lease"
    assert resp.json()["status"] == "classified"
    assert calls and calls[0][2] is False


def test_upload_document_mirror_uses_canonical_source_path_and_doc_type(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={
            "doc_type": "1042-S",
            "source_path": "Tax/2024/Form_1042-S.pdf",
        },
        files={"file": ("uploaded.pdf", b"tax-form", "application/pdf")},
    )

    assert resp.status_code == 200
    assert resp.json()["classification"] == "1042s"

    from compliance_os.web.models import database
    from compliance_os.web.models.tables_v2 import CheckRow as V2CheckRow
    from compliance_os.web.models.tables_v2 import DocumentRow as V2DocumentRow

    session = database._SessionLocal()
    try:
        bridge = session.query(V2CheckRow).filter_by(stage=f"{doc_mod.LEGACY_CASE_STAGE_PREFIX}{case_id}").first()
        assert bridge is not None
        mirrored = session.query(V2DocumentRow).filter_by(check_id=bridge.id).all()
        assert len(mirrored) == 1
        assert mirrored[0].doc_type == "1042s"
        assert mirrored[0].source_path == "Tax/2024/Form_1042-S.pdf"
        assert mirrored[0].provenance["classification"]["provided_doc_type"] == "1042-S"
        assert mirrored[0].provenance["ingestion"]["source_path"] == "Tax/2024/Form_1042-S.pdf"
    finally:
        session.close()


def test_upload_with_slot(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("w2.pdf", b"fake pdf", "text/plain")},
        data={"slot_key": "w2_latest"},
    )
    assert resp.json()["slot_key"] == "w2_latest"


def test_list_documents(client, case_id):
    client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("a.txt", b"aaa", "text/plain")},
    )
    client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("b.txt", b"bbb", "text/plain")},
    )
    resp = client.get(f"/api/cases/{case_id}/documents")
    assert len(resp.json()["documents"]) == 2


def test_delete_document(client, case_id):
    upload_resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("del.txt", b"delete me", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]
    del_resp = client.delete(f"/api/cases/{case_id}/documents/{doc_id}")
    assert del_resp.status_code == 200
    list_resp = client.get(f"/api/cases/{case_id}/documents")
    assert len(list_resp.json()["documents"]) == 0


def test_delete_document_reindexes_mirrored_versions(client, case_id):
    first = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_type": "employment_letter", "source_path": "employment/offer.pdf"},
        files={"file": ("offer.pdf", b"offer-v1", "application/pdf")},
    )
    second = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_type": "employment_letter", "source_path": "employment/offer.pdf"},
        files={"file": ("offer.pdf", b"offer-v2", "application/pdf")},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    from compliance_os.web.models import database
    from compliance_os.web.models.tables_v2 import CheckRow as V2CheckRow
    from compliance_os.web.models.tables_v2 import DocumentRow as V2DocumentRow

    session = database._SessionLocal()
    try:
        bridge = session.query(V2CheckRow).filter_by(stage=f"{doc_mod.LEGACY_CASE_STAGE_PREFIX}{case_id}").first()
        assert bridge is not None
        before_delete = (
            session.query(V2DocumentRow)
            .filter_by(check_id=bridge.id)
            .order_by(V2DocumentRow.document_version.asc())
            .all()
        )
        assert [doc.document_version for doc in before_delete] == [1, 2]
        assert [doc.is_active for doc in before_delete] == [False, True]
    finally:
        session.close()

    delete_resp = client.delete(f"/api/cases/{case_id}/documents/{second.json()['id']}")
    assert delete_resp.status_code == 200

    session = database._SessionLocal()
    try:
        bridge = session.query(V2CheckRow).filter_by(stage=f"{doc_mod.LEGACY_CASE_STAGE_PREFIX}{case_id}").first()
        assert bridge is not None
        after_delete = session.query(V2DocumentRow).filter_by(check_id=bridge.id).all()
        assert len(after_delete) == 1
        assert after_delete[0].document_version == 1
        assert after_delete[0].is_active is True
        assert after_delete[0].supersedes_document_id is None
    finally:
        session.close()


def test_update_slot_assignment(client, case_id):
    upload_resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("doc.txt", b"content", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]
    patch_resp = client.patch(
        f"/api/cases/{case_id}/documents/{doc_id}",
        json={"slot_key": "i20"},
    )
    assert patch_resp.json()["slot_key"] == "i20"


def test_update_document_normalizes_classification(client, case_id):
    upload_resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("doc.txt", b"content", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/cases/{case_id}/documents/{doc_id}",
        json={"classification": "1042-S"},
    )

    assert patch_resp.status_code == 200
    assert patch_resp.json()["classification"] == "1042s"


def test_update_document_syncs_mirrored_v2_classification(client, case_id):
    upload_resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("doc.txt", b"content", "text/plain")},
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/cases/{case_id}/documents/{doc_id}",
        json={"classification": "I-94"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["classification"] == "i94"

    from compliance_os.web.models import database
    from compliance_os.web.models.tables import DocumentRow as CaseDocumentRow
    from compliance_os.web.models.tables_v2 import CheckRow as V2CheckRow
    from compliance_os.web.models.tables_v2 import DocumentRow as V2DocumentRow

    session = database._SessionLocal()
    try:
        legacy_doc = session.get(CaseDocumentRow, doc_id)
        assert legacy_doc is not None
        bridge = session.query(V2CheckRow).filter_by(stage=f"{doc_mod.LEGACY_CASE_STAGE_PREFIX}{case_id}").first()
        assert bridge is not None
        mirrored = (
            session.query(V2DocumentRow)
            .filter_by(check_id=bridge.id, file_path=legacy_doc.file_path)
            .first()
        )
        assert mirrored is not None
        assert mirrored.doc_type == "i94"
        assert mirrored.provenance["classification"]["source"] == "legacy_patch"
        assert mirrored.provenance["classification"]["provided_doc_type"] == "I-94"
    finally:
        session.close()


def test_update_document_rejects_unknown_classification(client, case_id):
    upload_resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("doc.txt", b"content", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/cases/{case_id}/documents/{doc_id}",
        json={"classification": "totally_custom_type"},
    )

    assert patch_resp.status_code == 400


def test_checklist_from_discovery(client, case_id):
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"],
    })
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "tax_income_sources", "question_key": "tax_income_sources", "answer": ["W-2 employment"],
    })
    resp = client.get(f"/api/cases/{case_id}/documents/checklist")
    assert resp.status_code == 200
    slots = resp.json()["slots"]
    keys = [s["key"] for s in slots]
    assert "tax_w2" in keys


def test_reject_disallowed_file_type(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("malware.exe", b"bad", "application/x-msdownload")},
    )
    assert resp.status_code == 400
