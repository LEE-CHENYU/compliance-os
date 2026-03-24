"""Tests for Guardian check flow API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import Base as BaseV2, CheckRow, DocumentRow, ExtractedFieldRow


@pytest.fixture
def test_engine():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from compliance_os.web.models.database import Base as OldBase
    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_engine):
    SessionLocal = sessionmaker(bind=test_engine)

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_check(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "stem_opt", "years_in_us": 3}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["track"] == "stem_opt"
    assert data["answers"]["stage"] == "stem_opt"
    assert data["status"] == "intake"


def test_get_check(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {}})
    check_id = resp.json()["id"]
    resp = client.get(f"/api/checks/{check_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == check_id


def test_get_check_not_found(client):
    resp = client.get("/api/checks/nonexistent")
    assert resp.status_code == 404


def test_update_check_answers(client):
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {"stage": "opt"}})
    check_id = resp.json()["id"]
    resp = client.patch(f"/api/checks/{check_id}", json={"answers": {"years_in_us": 5}})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answers"]["stage"] == "opt"
    assert data["answers"]["years_in_us"] == 5


def test_comparisons_endpoint(client, db_session):
    # Create a check with pre-populated extracted fields
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    # Add i983 document with extracted fields
    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    db_session.add(doc_a)
    db_session.flush()
    for name, val in [("job_title", "Data Analyst"), ("employer_name", "Acme Corp"), ("compensation", "85000")]:
        db_session.add(ExtractedFieldRow(document_id=doc_a.id, field_name=name, field_value=val, confidence=0.9))

    # Add employment letter with extracted fields
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add(doc_b)
    db_session.flush()
    for name, val in [("job_title", "Business Ops Associate"), ("employer_name", "Acme Corp"), ("compensation", "85000")]:
        db_session.add(ExtractedFieldRow(document_id=doc_b.id, field_name=name, field_value=val, confidence=0.9))

    db_session.commit()

    # Run comparison
    resp = client.post(f"/api/checks/{check.id}/compare")
    assert resp.status_code == 200
    comparisons = resp.json()
    assert len(comparisons) > 0

    # Job title should mismatch
    job_title = next(c for c in comparisons if c["field_name"] == "job_title")
    assert job_title["status"] == "mismatch"

    # Employer name should match
    employer = next(c for c in comparisons if c["field_name"] == "employer_name")
    assert employer["status"] == "match"

    # Compensation should match
    comp = next(c for c in comparisons if c["field_name"] == "compensation")
    assert comp["status"] == "match"


def test_evaluate_endpoint(client, db_session):
    # Create check with comparisons already done
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt", "years_in_us": 3})
    db_session.add(check)
    db_session.flush()

    # Add documents + extracted fields (minimal)
    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add_all([doc_a, doc_b])
    db_session.commit()

    # Run compare first
    client.post(f"/api/checks/{check.id}/compare")

    # Run evaluate
    resp = client.post(f"/api/checks/{check.id}/evaluate")
    assert resp.status_code == 200
    findings = resp.json()
    assert isinstance(findings, list)


def test_followups_generated_from_mismatches(client, db_session):
    check = CheckRow(track="stem_opt", status="extracted", answers={"stage": "stem_opt"})
    db_session.add(check)
    db_session.flush()

    doc_a = DocumentRow(check_id=check.id, doc_type="i983", filename="i983.pdf", file_path="/tmp/i983.pdf", file_size=100, mime_type="application/pdf")
    doc_b = DocumentRow(check_id=check.id, doc_type="employment_letter", filename="letter.pdf", file_path="/tmp/letter.pdf", file_size=100, mime_type="application/pdf")
    db_session.add_all([doc_a, doc_b])
    db_session.flush()

    # Add mismatched extracted fields
    db_session.add(ExtractedFieldRow(document_id=doc_a.id, field_name="job_title", field_value="Data Analyst", confidence=0.9))
    db_session.add(ExtractedFieldRow(document_id=doc_b.id, field_name="job_title", field_value="Marketing Lead", confidence=0.9))
    db_session.commit()

    # Compare
    client.post(f"/api/checks/{check.id}/compare")

    # Generate followups
    resp = client.post(f"/api/checks/{check.id}/followups")
    assert resp.status_code == 200
    followups = resp.json()
    assert len(followups) > 0
    assert any("job_title" in f["question_key"] for f in followups)
