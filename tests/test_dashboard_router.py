"""Tests for dashboard data-room upload behavior."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import compliance_os.web.routers.dashboard as dashboard_mod
from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import (
    Base as BaseV2,
    CheckRow,
    ComparisonRow,
    DocumentRow,
    ExtractedFieldRow,
    FindingRow,
)
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


def test_dashboard_views_dedupe_duplicate_documents_events_and_risks(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-dedupe@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    start_date = (datetime.now(timezone.utc) - timedelta(days=430)).date().isoformat()
    end_date = (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()
    tax_new_id = None
    i983_new_id = None
    try:
        check_one = CheckRow(
            track="stem_opt",
            status="reviewed",
            user_id=user_id,
            answers={"stage": "stem_opt"},
        )
        check_two = CheckRow(
            track="stem_opt",
            status="reviewed",
            user_id=user_id,
            answers={"stage": "stem_opt"},
        )
        session.add_all([check_one, check_two])
        session.flush()

        tax_old = DocumentRow(
            check_id=check_one.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-old.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-same-hash",
            source_path="Tax/2024_TaxReturn.pdf",
            is_active=False,
            uploaded_at=now - timedelta(days=2),
        )
        tax_new = DocumentRow(
            check_id=check_two.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-new.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-same-hash",
            source_path="Tax/2024_TaxReturn.pdf",
            is_active=True,
            uploaded_at=now,
        )
        i983_old = DocumentRow(
            check_id=check_one.id,
            doc_type="i983",
            filename="i983.pdf",
            file_path=str(tmp_path / "i983-old.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="i983-same-hash",
            source_path="STEM/i983.pdf",
            is_active=False,
            uploaded_at=now - timedelta(days=1),
        )
        i983_new = DocumentRow(
            check_id=check_two.id,
            doc_type="i983",
            filename="i983.pdf",
            file_path=str(tmp_path / "i983-new.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="i983-same-hash",
            source_path="STEM/i983.pdf",
            is_active=True,
            uploaded_at=now,
        )
        session.add_all([tax_old, tax_new, i983_old, i983_new])
        session.flush()
        tax_new_id = tax_new.id
        i983_new_id = i983_new.id

        session.add_all(
            [
                ExtractedFieldRow(document_id=tax_old.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=tax_new.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=i983_old.id, field_name="start_date", field_value=start_date),
                ExtractedFieldRow(document_id=i983_old.id, field_name="end_date", field_value=end_date),
                ExtractedFieldRow(document_id=i983_new.id, field_name="start_date", field_value=start_date),
                ExtractedFieldRow(document_id=i983_new.id, field_name="end_date", field_value=end_date),
            ]
        )
        session.add_all(
            [
                FindingRow(
                    check_id=check_one.id,
                    rule_id="employment_start_mismatch",
                    severity="warning",
                    category="comparison",
                    title="Employment start date doesn't match I-983",
                    action="Verify correct date with DSO",
                    consequence="Unauthorized employment gap",
                    immigration_impact=True,
                ),
                FindingRow(
                    check_id=check_two.id,
                    rule_id="employment_start_mismatch",
                    severity="warning",
                    category="comparison",
                    title="Employment start date doesn't match I-983",
                    action="Verify correct date with DSO",
                    consequence="Unauthorized employment gap",
                    immigration_impact=True,
                ),
                FindingRow(
                    check_id=check_one.id,
                    rule_id="ar11_reminder",
                    severity="info",
                    category="advisory",
                    title="AR-11",
                    action="Upload related document",
                    consequence="Affects green card",
                    immigration_impact=True,
                ),
                FindingRow(
                    check_id=check_two.id,
                    rule_id="ar11_reminder",
                    severity="info",
                    category="advisory",
                    title="AR-11",
                    action="Upload related document",
                    consequence="Affects green card",
                    immigration_impact=True,
                ),
                ComparisonRow(
                    check_id=check_one.id,
                    field_name="employer_name",
                    value_a="Bitsync",
                    value_b="Bitsync",
                    match_type="exact",
                    status="match",
                    detail="same",
                ),
                ComparisonRow(
                    check_id=check_two.id,
                    field_name="employer_name",
                    value_a="Bitsync",
                    value_b="Bitsync",
                    match_type="exact",
                    status="match",
                    detail="same",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    docs_resp = client.get("/api/dashboard/documents", headers={"Authorization": f"Bearer {token}"})
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    assert len(docs) == 2
    assert {doc["filename"] for doc in docs} == {"2024_TaxReturn.pdf", "i983.pdf"}
    assert {doc["id"] for doc in docs} == {tax_new_id, i983_new_id}

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    tax_events = [event for event in timeline["events"] if event["title"] == "2024 Tax Return filed"]
    assert len(tax_events) == 1
    assert len(tax_events[0]["documents"]) == 1
    assert tax_events[0]["documents"][0]["id"] == tax_new_id

    stem_events = [event for event in timeline["events"] if event["title"] == "STEM OPT started"]
    assert len(stem_events) == 1

    today_events = [event for event in timeline["events"] if event["type"] == "now"]
    assert len(today_events) == 1
    assert len(today_events[0]["risks"]) == 1
    assert len(timeline["findings"]) == 1
    assert len(timeline["advisories"]) == 1

    prompt_types = {prompt["doc_type"] for prompt in timeline["upload_prompts"]}
    assert prompt_types == {"employment_letter", "i983_evaluation"}

    deadline_titles = [deadline["title"] for deadline in timeline["deadlines"]]
    assert deadline_titles.count("I-983 12-month evaluation due") == 1
    assert deadline_titles.count("OPT/STEM authorization ends") == 1
    assert deadline_titles.count("60-day grace period ends") == 1
    assert sum(1 for title in deadline_titles if title.endswith("Tax return due")) == 1

    stats_resp = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
    assert stats_resp.status_code == 200
    assert stats_resp.json()["documents"] == 2
    assert stats_resp.json()["risks"] == 1
    assert stats_resp.json()["verified"] == 1
