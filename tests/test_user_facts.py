from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import compliance_os.web.routers.user_facts as facts_router
from compliance_os.web.models.tables_v2 import Base, CheckRow, DocumentRow, UserFactRow
from compliance_os.web.services.document_store import _project_to_user_facts
from compliance_os.web.services.user_facts import record_conflict, resolve_conflict, upsert_fact


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_upsert_same_value_promotes_existing_fact_to_decision_lock():
    db = _session()
    try:
        original, superseded = upsert_fact(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            value="Acme Inc.",
            source_type="document",
            source_ref={"document_id": "doc-1"},
        )
        assert superseded is None

        locked, superseded = upsert_fact(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            value="Acme Inc.",
            source_type="decision_lock",
            source_ref={"ui_path": "/dashboard/facts"},
        )

        assert locked.id == original.id
        assert superseded is None
        assert locked.source_type == "decision_lock"
        assert locked.source_ref == {"ui_path": "/dashboard/facts"}
    finally:
        db.close()


def test_keep_current_conflict_resolution_locks_existing_value():
    db = _session()
    try:
        row, _ = upsert_fact(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            value="Acme Inc.",
            source_type="document",
            source_ref={"document_id": "doc-1"},
        )
        record_conflict(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            claimed_value="Other Inc.",
            source_ref={"document_id": "doc-2"},
        )

        resolved = resolve_conflict(
            db,
            user_id="user-1",
            fact_id=row.id,
            choice="keep_current",
        )

        assert resolved.id == row.id
        assert resolved.value == {"v": "Acme Inc."}
        assert resolved.source_type == "decision_lock"
        assert resolved.detected_conflicts == []
        assert resolved.source_ref["resolution"] == "keep_current"
    finally:
        db.close()


def test_use_new_conflict_resolution_locks_claimed_value():
    db = _session()
    try:
        row, _ = upsert_fact(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            value="Acme Inc.",
            source_type="document",
            source_ref={"document_id": "doc-1"},
        )
        record_conflict(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            claimed_value="Other Inc.",
            source_ref={"document_id": "doc-2"},
        )

        resolved = resolve_conflict(
            db,
            user_id="user-1",
            fact_id=row.id,
            choice="use_new",
        )

        assert resolved.id != row.id
        assert resolved.value == {"v": "Other Inc."}
        assert resolved.source_type == "decision_lock"
        assert resolved.source_ref["document_id"] == "doc-2"
        assert resolved.source_ref["resolution"] == f"use_new:{row.id}"
        superseded = db.get(UserFactRow, row.id)
        assert superseded.is_active is False
        assert superseded.superseded_by_id == resolved.id
    finally:
        db.close()


def test_facts_api_post_creates_decision_lock(client):
    register = client.post("/api/auth/register", json={"email": "facts-lock@example.com", "password": "secure123"})
    token = register.json()["token"]

    response = client.post(
        "/api/facts",
        headers={"Authorization": f"Bearer {token}"},
        json={"fact_key": "current_employer_legal_name", "value": "Acme Inc."},
    )

    assert response.status_code == 200
    assert response.json()["fact"]["source_type"] == "decision_lock"


def test_facts_summary_returns_local_fallback_when_llm_unavailable(client, monkeypatch):
    def fail_chat_completion(**_kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(facts_router, "chat_completion", fail_chat_completion)
    register = client.post("/api/auth/register", json={"email": "facts-summary@example.com", "password": "secure123"})
    token = register.json()["token"]
    client.post(
        "/api/facts",
        headers={"Authorization": f"Bearer {token}"},
        json={"fact_key": "current_employer_legal_name", "value": "Acme Inc."},
    )

    response = client.get("/api/facts/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["generated_by"] == "local"
    assert "Acme Inc." in body["summary"]


def test_document_projection_does_not_downgrade_matching_decision_lock():
    db = _session()
    try:
        check = CheckRow(track="stem_opt", user_id="user-1")
        db.add(check)
        db.flush()
        doc = DocumentRow(
            check_id=check.id,
            doc_type="w2",
            filename="w2.pdf",
            file_path="/tmp/w2.pdf",
            file_size=10,
            mime_type="application/pdf",
        )
        db.add(doc)
        db.flush()
        locked, _ = upsert_fact(
            db,
            user_id="user-1",
            fact_key="current_employer_legal_name",
            value="Acme Inc.",
            source_type="decision_lock",
            source_ref={"ui_path": "/dashboard/facts"},
        )

        _project_to_user_facts(
            db,
            doc=doc,
            field_name="employer_name",
            value="Acme Inc.",
            confidence=0.99,
        )

        db.refresh(locked)
        assert locked.is_active is True
        assert locked.source_type == "decision_lock"
        assert locked.source_ref == {"ui_path": "/dashboard/facts"}
    finally:
        db.close()
