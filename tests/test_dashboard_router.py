"""Tests for dashboard data-room upload behavior."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import compliance_os.web.routers.dashboard as dashboard_mod
from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import Base as BaseV2, DocumentRow
from compliance_os.web.services.document_intake import ResolvedDocumentType


@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from compliance_os.web.models.database import Base as OldBase

    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    from compliance_os.web.models.auth import UserRow  # noqa: F401

    BaseV2.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    original_upload_dir = dashboard_mod.UPLOAD_DIR
    dashboard_mod.UPLOAD_DIR = tmp_path / "uploads"
    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    dashboard_mod.UPLOAD_DIR = original_upload_dir


def test_dashboard_upload_can_infer_doc_type_when_omitted(client, monkeypatch):
    monkeypatch.setattr(
        dashboard_mod,
        "extract_into_document",
        lambda doc, db: {"document_id": doc.id, "doc_type": doc.doc_type},
    )
    monkeypatch.setattr(
        dashboard_mod,
        "resolve_document_type",
        lambda file_path, mime_type, *, provided_doc_type=None, allow_ocr=False: ResolvedDocumentType(
            doc_type="lease",
            confidence="high",
            source="filename",
            provided_doc_type=provided_doc_type,
        ),
    )

    register = client.post("/api/auth/register", json={"email": "dashboard@example.com", "password": "secure123"})
    token = register.json()["token"]

    resp = client.post(
        "/api/dashboard/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"source_path": "Lease/sublease agreement.pdf"},
        files={"file": ("sublease agreement.pdf", b"lease-1", "application/pdf")},
    )

    assert resp.status_code == 200
    doc_id = resp.json()["document_id"]

    doc_resp = client.get("/api/dashboard/documents", headers={"Authorization": f"Bearer {token}"})
    uploaded = next(doc for doc in doc_resp.json() if doc["id"] == doc_id)
    assert uploaded["doc_type"] == "lease"

    session = next(app.dependency_overrides[get_session]())
    try:
        stored = session.get(DocumentRow, doc_id)
        assert stored.doc_type == "lease"
        assert stored.provenance["classification"]["source"] == "filename"
    finally:
        session.close()


def test_dashboard_upload_persists_ingestion_issue_summary_for_generic_image(client, monkeypatch):
    monkeypatch.setattr(
        dashboard_mod,
        "extract_into_document",
        lambda doc, db: {"document_id": doc.id, "doc_type": doc.doc_type},
    )
    monkeypatch.setattr(
        dashboard_mod,
        "resolve_document_type",
        lambda file_path, mime_type, *, provided_doc_type=None, allow_ocr=False: ResolvedDocumentType(
            doc_type="passport",
            confidence="high",
            source="filename",
            provided_doc_type=provided_doc_type,
        ),
    )

    register = client.post("/api/auth/register", json={"email": "dashboard-issues@example.com", "password": "secure123"})
    token = register.json()["token"]

    resp = client.post(
        "/api/dashboard/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("IMG_0007.jpeg", b"image-bytes", "image/jpeg")},
    )

    assert resp.status_code == 200
    session = next(app.dependency_overrides[get_session]())
    try:
        stored = session.get(DocumentRow, resp.json()["document_id"])
        assert stored.provenance["ingestion_detection"]["issue_count"] == 2
        assert set(stored.provenance["ingestion_detection"]["issue_codes"]) == {
            "generic_source_name",
            "image_context_low_signal",
        }
    finally:
        session.close()
