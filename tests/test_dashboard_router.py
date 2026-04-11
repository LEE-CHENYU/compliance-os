"""Tests for dashboard data-room upload behavior."""

from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import compliance_os.web.routers.dashboard as dashboard_mod
import compliance_os.web.routers.form8843 as form8843_mod
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


def test_dashboard_today_risks_include_evidence_documents_from_rule_backfill(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-risk-docs@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add(check)
        session.flush()

        i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983.pdf",
            file_path=str(tmp_path / "i983.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="i983-hash",
            source_path="employment/VCV/i983.pdf",
        )
        letter = DocumentRow(
            check_id=check.id,
            doc_type="employment_letter",
            filename="letter.pdf",
            file_path=str(tmp_path / "letter.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="letter-hash",
            source_path="employment/VCV/letter.pdf",
        )
        session.add_all([i983, letter])
        session.flush()

        mismatch = ComparisonRow(
            check_id=check.id,
            field_name="start_date",
            value_a="2024-10-01",
            value_b="2024-10-15",
            match_type="exact",
            status="mismatch",
            confidence=0.0,
            detail="Different dates",
        )
        session.add(mismatch)
        session.flush()

        session.add(
            FindingRow(
                check_id=check.id,
                rule_id="start_date_mismatch",
                severity="warning",
                category="comparison",
                title="Employment start date doesn't match I-983",
                action="Verify correct date with DSO and file correction if needed",
                consequence="Unauthorized employment gap",
                immigration_impact=True,
            )
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    today_event = next(event for event in timeline_resp.json()["events"] if event["type"] == "now")
    risk = next(risk for risk in today_event["risks"] if risk["rule_id"] == "start_date_mismatch")

    assert {doc["filename"] for doc in risk["documents"]} == {"i983.pdf", "letter.pdf"}


def test_dashboard_upload_prepare_flags_hash_duplicates(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        dashboard_mod,
        "resolve_document_type",
        lambda file_path, mime_type, *, provided_doc_type=None, allow_ocr=False: ResolvedDocumentType(
            doc_type="tax_return",
            confidence="high",
            source="filename",
            provided_doc_type=provided_doc_type,
        ),
    )

    register = client.post("/api/auth/register", json={"email": "dashboard-prepare@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    existing_bytes = b"same-pdf-content"
    existing_hash = hashlib.sha256(existing_bytes).hexdigest()
    session = next(app.dependency_overrides[get_session]())
    try:
        check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={})
        session.add(check)
        session.flush()
        session.add(
            DocumentRow(
                check_id=check.id,
                doc_type="tax_return",
                filename="2024_TaxReturn.pdf",
                file_path=str(tmp_path / "existing.pdf"),
                file_size=len(existing_bytes),
                mime_type="application/pdf",
                content_hash=existing_hash,
                source_path="Tax/2024_TaxReturn.pdf",
                uploaded_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    finally:
        session.close()

    resp = client.post(
        "/api/dashboard/upload/prepare",
        headers={"Authorization": f"Bearer {token}"},
        data={"source_paths_json": json.dumps(["Tax/2024_TaxReturn.pdf", "Tax/2023_TaxReturn.pdf"])},
        files=[
            ("files", ("2024_TaxReturn.pdf", existing_bytes, "application/pdf")),
            ("files", ("2023_TaxReturn.pdf", b"brand-new-content", "application/pdf")),
        ],
    )

    assert resp.status_code == 200
    body = resp.json()["files"]
    assert body[0]["status"] == "duplicate"
    assert body[0]["resolved_doc_type"] == "tax_return"
    assert body[0]["duplicates"][0]["filename"] == "2024_TaxReturn.pdf"
    assert body[1]["status"] == "ready"
    assert body[1]["duplicates"] == []


def test_dashboard_upload_duplicate_action_asks_then_keeps(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        dashboard_mod,
        "extract_into_document",
        lambda doc, db: {"document_id": doc.id, "doc_type": doc.doc_type},
    )
    monkeypatch.setattr(
        dashboard_mod,
        "resolve_document_type",
        lambda file_path, mime_type, *, provided_doc_type=None, allow_ocr=False: ResolvedDocumentType(
            doc_type="tax_return",
            confidence="high",
            source="filename",
            provided_doc_type=provided_doc_type,
        ),
    )

    register = client.post("/api/auth/register", json={"email": "dashboard-duplicate@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    duplicate_bytes = b"same-upload"
    duplicate_hash = hashlib.sha256(duplicate_bytes).hexdigest()
    session = next(app.dependency_overrides[get_session]())
    try:
        check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={})
        session.add(check)
        session.flush()
        session.add(
            DocumentRow(
                check_id=check.id,
                doc_type="tax_return",
                filename="existing.pdf",
                file_path=str(tmp_path / "existing.pdf"),
                file_size=len(duplicate_bytes),
                mime_type="application/pdf",
                content_hash=duplicate_hash,
                source_path="Tax/existing.pdf",
                uploaded_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    finally:
        session.close()


def test_dashboard_timeline_maps_documents_to_specific_events_and_collapses_legacy_aliases(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-event-map@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        check_one = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        check_two = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add_all([check_one, check_two])
        session.flush()

        tax_2024_legacy = DocumentRow(
            check_id=check_one.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-2024-legacy.pdf"),
            file_size=617644,
            mime_type="application/pdf",
            content_hash=None,
            source_path="2024_TaxReturn.pdf",
            uploaded_at=now - timedelta(days=2),
        )
        tax_2024 = DocumentRow(
            check_id=check_two.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-2024.pdf"),
            file_size=617644,
            mime_type="application/pdf",
            content_hash="tax-2024-hash",
            source_path="/Users/lichenyu/Desktop/Important Docs /Tax/2024/2024_TaxReturn.pdf",
            uploaded_at=now,
        )
        tax_2023 = DocumentRow(
            check_id=check_two.id,
            doc_type="tax_return",
            filename="2023_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-2023.pdf"),
            file_size=515737,
            mime_type="application/pdf",
            content_hash="tax-2023-hash",
            source_path="/Users/lichenyu/Desktop/Important Docs /Tax/2023/2023_TaxReturn.pdf",
            uploaded_at=now,
        )
        i983_wolff = DocumentRow(
            check_id=check_one.id,
            doc_type="i983",
            filename="i983-wolff-and-li.pdf",
            file_path=str(tmp_path / "i983-wolff.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-wolff",
            source_path="employment/Wolff/i983-wolff-and-li.pdf",
            uploaded_at=now,
        )
        i983_bitsync = DocumentRow(
            check_id=check_two.id,
            doc_type="i983",
            filename="Chenyu_i983 Form_100124_ink_signed.pdf",
            file_path=str(tmp_path / "i983-bitsync.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-bitsync",
            source_path="employment/Bitsync/Chenyu_i983 Form_100124_ink_signed.pdf",
            uploaded_at=now,
        )
        offer_wolff = DocumentRow(
            check_id=check_one.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-wolff.pdf"),
            file_size=140,
            mime_type="application/pdf",
            content_hash="offer-wolff",
            source_path="employment/Wolff/Wolff_&_Li_Capital_Offer_Letter.pdf",
            uploaded_at=now,
        )
        offer_bitsync = DocumentRow(
            check_id=check_two.id,
            doc_type="employment_letter",
            filename="signed offer letter bitsync.pdf",
            file_path=str(tmp_path / "offer-bitsync.pdf"),
            file_size=140,
            mime_type="application/pdf",
            content_hash="offer-bitsync",
            source_path="employment/Bitsync/signed offer letter bitsync.pdf",
            uploaded_at=now,
        )
        session.add_all(
            [
                tax_2024_legacy,
                tax_2024,
                tax_2023,
                i983_wolff,
                i983_bitsync,
                offer_wolff,
                offer_bitsync,
            ]
        )
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=tax_2024_legacy.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=tax_2024.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=tax_2023.id, field_name="tax_year", field_value="2023"),
                ExtractedFieldRow(document_id=i983_wolff.id, field_name="start_date", field_value="2024-01-23"),
                ExtractedFieldRow(document_id=i983_wolff.id, field_name="employer_name", field_value="Wolff & Li Capital"),
                ExtractedFieldRow(document_id=i983_bitsync.id, field_name="start_date", field_value="2024-10-01"),
                ExtractedFieldRow(document_id=i983_bitsync.id, field_name="employer_name", field_value="Bitsync"),
                ExtractedFieldRow(document_id=offer_wolff.id, field_name="start_date", field_value="2024-01-23"),
                ExtractedFieldRow(document_id=offer_wolff.id, field_name="employer_name", field_value="Wolff & Li Capital"),
                ExtractedFieldRow(document_id=offer_bitsync.id, field_name="start_date", field_value="2024-10-01"),
                ExtractedFieldRow(document_id=offer_bitsync.id, field_name="employer_name", field_value="Bitsync"),
            ]
        )
        session.commit()
    finally:
        session.close()

    docs_resp = client.get("/api/dashboard/documents", headers={"Authorization": f"Bearer {token}"})
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    assert [doc["filename"] for doc in docs].count("2024_TaxReturn.pdf") == 1

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    tax_2023_event = next(event for event in timeline["events"] if event["title"] == "2023 Tax Return filed")
    assert {doc["filename"] for doc in tax_2023_event["documents"]} == {"2023_TaxReturn.pdf"}

    tax_2024_event = next(event for event in timeline["events"] if event["title"] == "2024 Tax Return filed")
    assert len([event for event in timeline["events"] if event["title"] == "2024 Tax Return filed"]) == 1
    assert {doc["filename"] for doc in tax_2024_event["documents"]} == {"2024_TaxReturn.pdf"}

    wolff_event = next(
        event for event in timeline["events"]
        if event["title"] == "STEM OPT started" and event["date"] == "2024-01-23"
    )
    assert wolff_event["chain"]["type"] == "employment"
    assert wolff_event["chain"]["label"] == "Wolff & Li Capital"
    assert {doc["filename"] for doc in wolff_event["documents"]} == {
        "i983-wolff-and-li.pdf",
        "Wolff_&_Li_Capital_Offer_Letter.pdf",
    }

    bitsync_event = next(
        event for event in timeline["events"]
        if event["title"] == "STEM OPT started" and event["date"] == "2024-10-01"
    )
    assert bitsync_event["chain"]["type"] == "employment"
    assert bitsync_event["chain"]["label"] == "Bitsync"
    assert {doc["filename"] for doc in bitsync_event["documents"]} == {
        "Chenyu_i983 Form_100124_ink_signed.pdf",
        "signed offer letter bitsync.pdf",
    }


def test_dashboard_timeline_prefers_signed_supported_stem_start_events(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-signed-stem@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add(check)
        session.flush()

        vcv_i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="Chenyu_i983 Form_100124_ink_signed.pdf",
            file_path=str(tmp_path / "i983-vcv.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-vcv",
            source_path="stem opt/i983/vcv/Chenyu_i983 Form_100124_ink_signed.pdf",
            uploaded_at=now,
        )
        wolff_i983_unsigned = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983-wolff-and-li.pdf",
            file_path=str(tmp_path / "i983-wolff-unsigned.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-wolff-unsigned",
            source_path="stem opt/i983/wolff-and-li/i983-wolff-and-li.pdf",
            uploaded_at=now,
        )
        wolff_i983_signed = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983-wolff-and-li-signed.pdf",
            file_path=str(tmp_path / "i983-wolff-signed.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-wolff-signed",
            source_path="stem opt/i983/wolff-and-li/i983-wolff-and-li-signed.pdf",
            uploaded_at=now,
        )
        wolff_offer = DocumentRow(
            check_id=check.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-wolff.pdf"),
            file_size=140,
            mime_type="application/pdf",
            content_hash="offer-wolff",
            source_path="employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf",
            uploaded_at=now,
        )
        session.add_all([vcv_i983, wolff_i983_unsigned, wolff_i983_signed, wolff_offer])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=vcv_i983.id, field_name="start_date", field_value="2024-10-01"),
                ExtractedFieldRow(document_id=vcv_i983.id, field_name="employer_name", field_value="Tiger Cloud LLC"),
                ExtractedFieldRow(document_id=wolff_i983_unsigned.id, field_name="start_date", field_value="2024-01-23"),
                ExtractedFieldRow(document_id=wolff_i983_unsigned.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_i983_signed.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=wolff_i983_signed.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    stem_events = [
        event for event in timeline["events"]
        if event["title"] == "STEM OPT started"
    ]
    assert [event["date"] for event in stem_events] == ["2024-10-01", "2025-03-17"]

    vcv_event = next(event for event in stem_events if event["date"] == "2024-10-01")
    assert vcv_event["chain"]["label"] == "Tiger Cloud LLC (vcv)"
    assert {doc["filename"] for doc in vcv_event["documents"]} == {
        "Chenyu_i983 Form_100124_ink_signed.pdf",
    }

    wolff_event = next(event for event in stem_events if event["date"] == "2025-03-17")
    assert wolff_event["chain"]["label"] == "Wolff & Li Capital Inc."
    assert {doc["filename"] for doc in wolff_event["documents"]} == {
        "i983-wolff-and-li-signed.pdf",
        "Wolff_&_Li_Capital_Offer_Letter.pdf",
    }
    assert not any(
        event for event in timeline["events"]
        if event["title"] == "STEM OPT ends" and event["date"] == "2026-01-22"
    )

    chains_resp = client.get("/api/dashboard/chains", headers={"Authorization": f"Bearer {token}"})
    assert chains_resp.status_code == 200
    chains = {chain["chain_key"]: chain for chain in chains_resp.json() if chain["chain_type"] == "employment"}
    assert chains["employment:wolff-li-capital-inc:2024-01-23"]["status"] == "superseded"
    assert chains["employment:wolff-li-capital-inc:2025-03-17"]["status"] == "active"


def test_dashboard_timeline_and_chains_use_canonical_document_ids_for_equivalent_duplicates(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-canonical-ids@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]
    i983_new_id = None
    tax_new_id = None

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        stem_check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        entity_check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={"entity_type": "smllc"})
        session.add_all([stem_check, entity_check])
        session.flush()

        i983_old = DocumentRow(
            check_id=stem_check.id,
            doc_type="i983",
            filename="i983-wolff-and-li-signed.pdf",
            file_path=str(tmp_path / "i983-old.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="shared-i983-hash",
            source_path="employment/Wolff/i983-wolff-and-li-signed.pdf",
            is_active=False,
            uploaded_at=now - timedelta(days=1),
        )
        i983_new = DocumentRow(
            check_id=stem_check.id,
            doc_type="i983",
            filename="i983-wolff-and-li-signed.pdf",
            file_path=str(tmp_path / "i983-new.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="shared-i983-hash",
            source_path="employment/Wolff/i983-wolff-and-li-signed.pdf",
            is_active=True,
            uploaded_at=now,
        )
        tax_old = DocumentRow(
            check_id=entity_check.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-old.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="shared-tax-hash",
            source_path="Tax/2024/2024_TaxReturn.pdf",
            is_active=False,
            uploaded_at=now - timedelta(days=1),
        )
        tax_new = DocumentRow(
            check_id=entity_check.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-new.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="shared-tax-hash",
            source_path="Tax/2024/2024_TaxReturn.pdf",
            is_active=True,
            uploaded_at=now,
        )
        session.add_all([i983_old, i983_new, tax_old, tax_new])
        session.flush()
        i983_new_id = i983_new.id
        tax_new_id = tax_new.id

        session.add_all(
            [
                ExtractedFieldRow(document_id=i983_old.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=i983_old.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=i983_new.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=i983_new.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=tax_old.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=tax_old.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=tax_new.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=tax_new.id, field_name="tax_year", field_value="2024"),
            ]
        )
        session.commit()
    finally:
        session.close()

    docs_resp = client.get("/api/dashboard/documents", headers={"Authorization": f"Bearer {token}"})
    assert docs_resp.status_code == 200
    visible_doc_ids = {doc["id"] for doc in docs_resp.json()}
    assert visible_doc_ids == {i983_new_id, tax_new_id}

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    stem_event = next(
        event for event in timeline["events"]
        if event["title"] == "STEM OPT started" and event["date"] == "2025-03-17"
    )
    assert {doc["id"] for doc in stem_event["documents"]} == {i983_new_id}

    tax_event = next(event for event in timeline["events"] if event["title"] == "2024 Tax Return filed")
    assert {doc["id"] for doc in tax_event["documents"]} == {tax_new_id}

    chains_resp = client.get("/api/dashboard/chains", headers={"Authorization": f"Bearer {token}"})
    assert chains_resp.status_code == 200
    chains = {chain["chain_key"]: chain for chain in chains_resp.json()}
    assert {doc["document_id"] for doc in chains["employment:wolff-li-capital-inc:2025-03-17"]["documents"]} == {i983_new_id}
    assert {doc["document_id"] for doc in chains["entity:bamboo-shoot-growth-capital-llc"]["documents"]} == {tax_new_id}


def test_dashboard_timeline_keeps_same_day_employment_chains_separate(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-same-day-chains@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add(check)
        session.flush()

        wolff_i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983-wolff-and-li-signed.pdf",
            file_path=str(tmp_path / "i983-wolff-signed.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-wolff-signed",
            source_path="stem opt/i983/wolff-and-li/i983-wolff-and-li-signed.pdf",
            uploaded_at=now,
        )
        wolff_offer = DocumentRow(
            check_id=check.id,
            doc_type="employment_letter",
            filename="Wolff_&_Li_Capital_Offer_Letter.pdf",
            file_path=str(tmp_path / "offer-wolff.pdf"),
            file_size=140,
            mime_type="application/pdf",
            content_hash="offer-wolff",
            source_path="employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf",
            uploaded_at=now,
        )
        tiger_i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="vcv-i983-signed.pdf",
            file_path=str(tmp_path / "i983-vcv-signed.pdf"),
            file_size=120,
            mime_type="application/pdf",
            content_hash="i983-vcv-signed",
            source_path="stem opt/i983/vcv/vcv-i983-signed.pdf",
            uploaded_at=now,
        )
        tiger_offer = DocumentRow(
            check_id=check.id,
            doc_type="employment_letter",
            filename="Employer Letter_VCV_Full Time.docx",
            file_path=str(tmp_path / "offer-vcv.docx"),
            file_size=140,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content_hash="offer-vcv",
            source_path="stem opt/letter/Employer Letter_VCV_Full Time.docx",
            uploaded_at=now,
        )
        session.add_all([wolff_i983, wolff_offer, tiger_i983, tiger_offer])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=wolff_i983.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=wolff_i983.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=wolff_offer.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=tiger_i983.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=tiger_i983.id, field_name="employer_name", field_value="Tiger Cloud LLC"),
                ExtractedFieldRow(document_id=tiger_offer.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=tiger_offer.id, field_name="employer_name", field_value="Tiger Cloud LLC"),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    stem_events = [
        event for event in timeline["events"]
        if event["title"] == "STEM OPT started" and event["date"] == "2025-03-17"
    ]
    assert len(stem_events) == 2
    assert {event["chain"]["label"] for event in stem_events} == {
        "Tiger Cloud LLC (vcv)",
        "Wolff & Li Capital Inc.",
    }


def test_dashboard_timeline_includes_payroll_and_entity_milestones(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-chain-events@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        employment_check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "employment"})
        entity_check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={"entity_type": "smllc"})
        session.add_all([employment_check, entity_check])
        session.flush()

        claudius_paystub = DocumentRow(
            check_id=employment_check.id,
            doc_type="paystub",
            filename="chenyu-li-paystub-2025-02-25.pdf",
            file_path=str(tmp_path / "claudius-paystub.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="claudius-paystub",
            source_path="employment/Claudius/chenyu-li-paystub-2025-02-25.pdf",
            uploaded_at=now,
        )
        articles = DocumentRow(
            check_id=entity_check.id,
            doc_type="articles_of_organization",
            filename="Articles of Organization.pdf",
            file_path=str(tmp_path / "articles.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="articles-1",
            source_path="business/Bamboo/Articles of Organization.pdf",
            uploaded_at=now - timedelta(days=5),
        )
        ein_letter = DocumentRow(
            check_id=entity_check.id,
            doc_type="ein_letter",
            filename="CP575Notice_1686945041312.pdf",
            file_path=str(tmp_path / "cp575.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="ein-letter-1",
            source_path="business/Bamboo/CP575Notice_1686945041312.pdf",
            uploaded_at=now - timedelta(days=4),
        )
        tax_return = DocumentRow(
            check_id=entity_check.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-return.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-2024",
            source_path="business/Bamboo/2024_TaxReturn.pdf",
            uploaded_at=now - timedelta(days=2),
        )
        session.add_all([claudius_paystub, articles, ein_letter, tax_return])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=claudius_paystub.id, field_name="employer_name", field_value="Claudius Legal Intelligence Inc"),
                ExtractedFieldRow(document_id=claudius_paystub.id, field_name="pay_date", field_value="2025-02-25"),
                ExtractedFieldRow(document_id=articles.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=articles.id, field_name="filing_date", field_value="2023-06-16"),
                ExtractedFieldRow(document_id=ein_letter.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=ein_letter.id, field_name="assigned_date", field_value="2023-06-20"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="entity_name", field_value="Bamboo Shoot Growth Capital LLC"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="tax_year", field_value="2024"),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    payroll_event = next(event for event in timeline["events"] if event["title"] == "Payroll observed")
    assert payroll_event["date"] == "2025-02-25"
    assert payroll_event["chain"]["label"] == "Claudius Legal Intelligence Inc"
    assert {doc["filename"] for doc in payroll_event["documents"]} == {"chenyu-li-paystub-2025-02-25.pdf"}

    formation_event = next(event for event in timeline["events"] if event["title"] == "Entity formed")
    assert formation_event["date"] == "2023-06-16"
    assert formation_event["chain"]["label"] == "Bamboo Shoot Growth Capital LLC"
    assert {doc["filename"] for doc in formation_event["documents"]} == {"Articles of Organization.pdf"}

    ein_event = next(event for event in timeline["events"] if event["title"] == "EIN assigned")
    assert ein_event["date"] == "2023-06-20"
    assert {doc["filename"] for doc in ein_event["documents"]} == {"CP575Notice_1686945041312.pdf"}

    tax_events = [event for event in timeline["events"] if event["title"] == "2024 Tax Return filed"]
    assert len(tax_events) == 1
    assert {doc["filename"] for doc in tax_events[0]["documents"]} == {"2024_TaxReturn.pdf"}


def test_dashboard_timeline_surfaces_integrity_issues_for_mapping_gaps(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-integrity@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        check_one = CheckRow(track="data_room", status="reviewed", user_id=user_id, answers={})
        check_two = CheckRow(track="data_room", status="reviewed", user_id=user_id, answers={})
        session.add_all([check_one, check_two])
        session.flush()

        tax_old = DocumentRow(
            check_id=check_one.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-1.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-shared-hash",
            source_path="Tax/2024_TaxReturn.pdf",
        )
        tax_new = DocumentRow(
            check_id=check_two.id,
            doc_type="tax_return",
            filename="2024_TaxReturn.pdf",
            file_path=str(tmp_path / "tax-2.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-shared-hash",
            source_path="Tax/2024_TaxReturn.pdf",
        )
        passport = DocumentRow(
            check_id=check_one.id,
            doc_type="passport",
            filename="passport.pdf",
            file_path=str(tmp_path / "passport.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="passport-hash",
            source_path="Identity/passport.pdf",
        )
        paystub = DocumentRow(
            check_id=check_one.id,
            doc_type="paystub",
            filename="paystub.pdf",
            file_path=str(tmp_path / "paystub.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="paystub-hash",
            source_path="employment/Claudius/paystub.pdf",
        )
        session.add_all([tax_old, tax_new, passport, paystub])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=tax_old.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=tax_new.id, field_name="tax_year", field_value="2024"),
                ExtractedFieldRow(document_id=paystub.id, field_name="employer_name", field_value="Claudius Inc"),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    integrity = timeline_resp.json()["integrity_issues"]

    duplicate_issue = next(issue for issue in integrity if issue["issue_code"] == "duplicate_across_checks")
    assert [doc["filename"] for doc in duplicate_issue["documents"]] == ["2024_TaxReturn.pdf"]

    unchained_issue = next(
        issue
        for issue in integrity
        if issue["issue_code"] == "unchained_document" and issue["documents"][0]["filename"] == "2024_TaxReturn.pdf"
    )
    assert unchained_issue["documents"][0]["doc_type"] == "tax_return"

    unmapped_issue = next(
        issue
        for issue in integrity
        if issue["issue_code"] == "unmapped_document" and issue["documents"][0]["filename"] == "passport.pdf"
    )
    assert unmapped_issue["documents"][0]["doc_type"] == "passport"

    untimed_issue = next(
        issue
        for issue in integrity
        if issue["issue_code"] == "untimed_document" and issue["documents"][0]["filename"] == "paystub.pdf"
    )
    assert untimed_issue["chains"][0]["label"] == "Claudius Inc"


def test_dashboard_timeline_surfaces_ambiguous_chain_links_for_shared_documents(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-ambiguous-chain@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        check_one = CheckRow(track="data_room", status="reviewed", user_id=user_id, answers={})
        check_two = CheckRow(track="data_room", status="reviewed", user_id=user_id, answers={})
        session.add_all([check_one, check_two])
        session.flush()

        alpha = DocumentRow(
            check_id=check_one.id,
            doc_type="employment_letter",
            filename="offer.pdf",
            file_path=str(tmp_path / "offer-alpha.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="offer-shared-hash",
            source_path="employment/Alpha/offer.pdf",
        )
        beta = DocumentRow(
            check_id=check_two.id,
            doc_type="employment_letter",
            filename="offer.pdf",
            file_path=str(tmp_path / "offer-beta.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="offer-shared-hash",
            source_path="employment/Beta/offer.pdf",
        )
        session.add_all([alpha, beta])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=alpha.id, field_name="employer_name", field_value="Alpha Labs"),
                ExtractedFieldRow(document_id=alpha.id, field_name="start_date", field_value="2024-06-01"),
                ExtractedFieldRow(document_id=beta.id, field_name="employer_name", field_value="Beta Works"),
                ExtractedFieldRow(document_id=beta.id, field_name="start_date", field_value="2025-01-15"),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    assert not any(issue["issue_code"] == "ambiguous_chain_link" for issue in timeline["integrity_issues"])
    prompt = next(prompt for prompt in timeline["assistant_prompts"] if prompt["issue_code"] == "ambiguous_chain_link")
    assert prompt["documents"][0]["filename"] == "offer.pdf"
    assert {chain["label"] for chain in prompt["chains"]} == {"Alpha Labs", "Beta Works"}

    integrity_resp = client.get("/api/dashboard/integrity", headers={"Authorization": f"Bearer {token}"})
    assert integrity_resp.status_code == 200
    ambiguous_issue = next(issue for issue in integrity_resp.json() if issue["issue_code"] == "ambiguous_chain_link")

    assert [doc["filename"] for doc in ambiguous_issue["documents"]] == ["offer.pdf"]
    assert {chain["label"] for chain in ambiguous_issue["chains"]} == {"Alpha Labs", "Beta Works"}

    respond_resp = client.post(
        "/api/dashboard/integrity/respond",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "prompt_id": prompt["id"],
            "document_id": prompt["documents"][0]["id"],
            "action": "attach_chain",
            "chain_key": next(chain["key"] for chain in prompt["chains"] if chain["label"] == "Alpha Labs"),
        },
    )
    assert respond_resp.status_code == 200

    refreshed_timeline = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"}).json()
    assert not any(item["issue_code"] == "ambiguous_chain_link" for item in refreshed_timeline["integrity_issues"])
    assert not any(item["issue_code"] == "ambiguous_chain_link" for item in refreshed_timeline["assistant_prompts"])


def test_dashboard_timeline_surfaces_conflicting_chain_evidence(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-conflicting-chain@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        check = CheckRow(track="entity", status="reviewed", user_id=user_id, answers={})
        session.add(check)
        session.flush()

        articles = DocumentRow(
            check_id=check.id,
            doc_type="articles_of_organization",
            filename="articles.pdf",
            file_path=str(tmp_path / "articles.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="articles-hash",
            source_path="business/Bamboo/articles.pdf",
        )
        ein_letter = DocumentRow(
            check_id=check.id,
            doc_type="ein_letter",
            filename="cp575.pdf",
            file_path=str(tmp_path / "cp575.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="ein-letter-hash",
            source_path="business/Bamboo/cp575.pdf",
        )
        tax_return = DocumentRow(
            check_id=check.id,
            doc_type="tax_return",
            filename="2024_return.pdf",
            file_path=str(tmp_path / "2024_return.pdf"),
            file_size=100,
            mime_type="application/pdf",
            content_hash="tax-bamboo-hash",
            source_path="business/Bamboo/2024_return.pdf",
        )
        session.add_all([articles, ein_letter, tax_return])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=articles.id, field_name="entity_name", field_value="Bamboo AI LLC"),
                ExtractedFieldRow(document_id=ein_letter.id, field_name="entity_name", field_value="Bamboo AI LLC"),
                ExtractedFieldRow(document_id=ein_letter.id, field_name="ein", field_value="12-3456789"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="entity_name", field_value="Bamboo AI LLC"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="ein", field_value="98-7654321"),
                ExtractedFieldRow(document_id=tax_return.id, field_name="tax_year", field_value="2024"),
            ]
        )
        session.commit()
    finally:
        session.close()

    integrity_resp = client.get("/api/dashboard/integrity", headers={"Authorization": f"Bearer {token}"})
    assert integrity_resp.status_code == 200
    conflict_issue = next(issue for issue in integrity_resp.json() if issue["issue_code"] == "conflicting_chain_evidence")

    assert conflict_issue["chains"][0]["label"] == "Bamboo AI LLC"
    assert {doc["filename"] for doc in conflict_issue["documents"]} == {"cp575.pdf", "2024_return.pdf"}
    assert any(field["field_name"] == "ein" for field in conflict_issue["details"]["fields"])


def test_dashboard_timeline_i983_evaluation_prompts_follow_active_stem_chains_only(client, tmp_path):
    register = client.post("/api/auth/register", json={"email": "dashboard-stem-eval@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    now = datetime.now(timezone.utc)
    try:
        check = CheckRow(track="stem_opt", status="reviewed", user_id=user_id, answers={"stage": "stem_opt"})
        session.add(check)
        session.flush()

        old_i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983-wolff-old.pdf",
            file_path=str(tmp_path / "old.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff/i983-wolff-old.pdf",
            uploaded_at=now - timedelta(days=2),
        )
        signed_i983 = DocumentRow(
            check_id=check.id,
            doc_type="i983",
            filename="i983-wolff-signed.pdf",
            file_path=str(tmp_path / "signed.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff/i983-wolff-signed.pdf",
            uploaded_at=now - timedelta(days=1),
        )
        offer = DocumentRow(
            check_id=check.id,
            doc_type="employment_letter",
            filename="WolffOffer.pdf",
            file_path=str(tmp_path / "offer.pdf"),
            file_size=100,
            mime_type="application/pdf",
            source_path="employment/Wolff/WolffOffer.pdf",
            uploaded_at=now,
        )
        session.add_all([old_i983, signed_i983, offer])
        session.flush()

        session.add_all(
            [
                ExtractedFieldRow(document_id=old_i983.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=old_i983.id, field_name="start_date", field_value="2024-01-23"),
                ExtractedFieldRow(document_id=old_i983.id, field_name="end_date", field_value="2026-01-22"),
                ExtractedFieldRow(document_id=signed_i983.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=signed_i983.id, field_name="start_date", field_value="2025-03-17"),
                ExtractedFieldRow(document_id=offer.id, field_name="employer_name", field_value="Wolff & Li Capital Inc."),
                ExtractedFieldRow(document_id=offer.id, field_name="start_date", field_value="2025-03-17"),
            ]
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    payload = timeline_resp.json()

    eval_dates = {prompt["event_date"] for prompt in payload["upload_prompts"] if prompt["doc_type"] == "i983_evaluation"}
    assert "2026-03-17" in eval_dates
    assert "2025-01-23" not in eval_dates

    deadline_dates = {item["date"] for item in payload["deadlines"] if item["title"] == "I-983 12-month evaluation due"}
    assert "2026-03-17" in deadline_dates
    assert "2025-01-23" not in deadline_dates


def test_dashboard_timeline_recommends_form_8843_for_current_student(client):
    register = client.post("/api/auth/register", json={"email": "dashboard-student-service@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        session.add(
            CheckRow(
                track="student",
                status="reviewed",
                user_id=user_id,
                answers={"stage": "pre_completion"},
            )
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    body = timeline_resp.json()

    recommendations = body["service_summary"]["recommended_services"]
    skus = [item["sku"] for item in recommendations]
    assert "form_8843_free" in skus
    form_8843 = next(item for item in recommendations if item["sku"] == "form_8843_free")
    assert form_8843["href"] == "/form-8843"
    assert "opt" in form_8843["reason"].lower() or "f-1" in form_8843["reason"].lower()


def test_dashboard_timeline_recommends_form_8843_for_f1_founder_on_entity_track(client):
    register = client.post("/api/auth/register", json={"email": "dashboard-founder-8843@example.com", "password": "secure123"})
    token = register.json()["token"]
    user_id = register.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        session.add(
            CheckRow(
                track="entity",
                status="reviewed",
                user_id=user_id,
                answers={
                    "owner_residency": "on_visa",
                    "visa_type": "f1_opt_stem",
                },
            )
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    recommendations = timeline_resp.json()["service_summary"]["recommended_services"]

    form_8843 = next(item for item in recommendations if item["sku"] == "form_8843_free")
    assert "running a company" in form_8843["reason"].lower()


def test_dashboard_timeline_surfaces_active_service_orders_and_service_deadlines(client, monkeypatch, tmp_path):
    monkeypatch.setattr(form8843_mod, "FORM_8843_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        form8843_mod,
        "send_form_8843_welcome",
        lambda *args, **kwargs: {"status": "skipped"},
    )

    register = client.post("/api/auth/register", json={"email": "dashboard-service-order@example.com", "password": "secure123"})
    token = register.json()["token"]

    generate = client.post(
        "/api/form8843/generate",
        json={
            "email": "dashboard-service-order@example.com",
            "full_name": "Dashboard Order",
            "visa_type": "F-1",
            "school_name": "Columbia University",
            "country_citizenship": "China",
            "days_present_current": 340,
            "days_present_year_1_ago": 280,
            "days_present_year_2_ago": 0,
        },
    )
    assert generate.status_code == 200
    order_id = generate.json()["order_id"]

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    body = timeline_resp.json()

    active_orders = body["service_summary"]["active_orders"]
    assert any(order["order_id"] == order_id for order in active_orders)
    active_order = next(order for order in active_orders if order["order_id"] == order_id)
    assert active_order["product_sku"] == "form_8843_free"
    assert active_order["href"] == f"/account/orders/{order_id}"
    assert active_order["next_action"] == "Print, sign, and mail your Form 8843."

    deadline_titles = {deadline["title"] for deadline in body["deadlines"]}
    assert "Form 8843 mailing deadline" in deadline_titles

    recommendation_skus = {item["sku"] for item in body["service_summary"]["recommended_services"]}
    assert "form_8843_free" not in recommendation_skus


def test_dashboard_service_center_collapses_duplicate_reusable_drafts(client):
    register = client.post("/api/auth/register", json={"email": "dashboard-draft-collapse@example.com", "password": "secure123"})
    token = register.json()["token"]

    first = client.post(
        "/api/marketplace/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"sku": "student_tax_1040nr"},
    )
    assert first.status_code == 200

    session = next(app.dependency_overrides[get_session]())
    try:
        from compliance_os.web.models.marketplace import MarketplaceUserRow, OrderRow

        marketplace_user = session.query(MarketplaceUserRow).filter(MarketplaceUserRow.email == "dashboard-draft-collapse@example.com").one()
        session.add(
            OrderRow(
                user_id=marketplace_user.id,
                product_sku="student_tax_1040nr",
                status="draft",
                amount_cents=2900,
                delivery_method="download_only",
                mailing_status="not_required",
                intake_data={"full_name": "Duplicate Draft"},
                result_data=None,
            )
        )
        session.commit()
    finally:
        session.close()

    timeline_resp = client.get("/api/dashboard/timeline", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200
    body = timeline_resp.json()

    active_orders = [order for order in body["service_summary"]["active_orders"] if order["product_sku"] == "student_tax_1040nr"]
    assert len(active_orders) == 1
