"""Test document upload and management API endpoints."""

import pytest

import compliance_os.web.routers.documents as doc_mod


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


def test_checklist_from_discovery(client, case_id):
    client.post(f"/api/cases/{case_id}/discovery", json={
        "step": "concern_area", "question_key": "concern_area", "answer": ["Tax Filing"],
    })
    resp = client.get(f"/api/cases/{case_id}/documents/checklist")
    assert resp.status_code == 200
    slots = resp.json()["slots"]
    keys = [s["key"] for s in slots]
    assert "w2_latest" in keys


def test_reject_disallowed_file_type(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("malware.exe", b"bad", "application/x-msdownload")},
    )
    assert resp.status_code == 400
