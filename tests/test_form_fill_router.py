"""Route coverage for form-fill APIs, including legacy dashboard aliases."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import Base as BaseV2
import compliance_os.web.routers.form_fill as form_fill_mod


def _auth_token(client: TestClient, email: str) -> str:
    register = client.post("/api/auth/register", json={"email": email, "password": "secure123"})
    assert register.status_code == 200
    return register.json()["token"]


def _pdf_upload() -> tuple[str, bytes, str]:
    return ("sample.pdf", b"%PDF-1.4 sample", "application/pdf")


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from compliance_os.web.models.database import Base as OldBase
    from compliance_os.web.models.auth import UserRow  # noqa: F401

    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_legacy_extract_route_still_works(client, monkeypatch):
    monkeypatch.setattr(
        form_fill_mod,
        "extract_acroform_fields",
        lambda _pdf_bytes: [{
            "field_name": "full_name",
            "field_type": "Text",
            "field_label": "Student Name",
            "field_context": "Full legal name of the student",
            "page": 0,
        }],
    )
    monkeypatch.setattr(form_fill_mod, "_build_context", lambda _user_id, _db: ("Known context", []))
    monkeypatch.setattr(
        form_fill_mod,
        "propose_field_values",
        lambda _fields, _context, instruction=None, usage_context=None: [
            {
                "field_name": "full_name",
                "proposed_value": "Alice Example",
                "confidence": "high",
                "source": "profile",
            }
        ],
    )

    token = _auth_token(client, "form-fill-extract@example.com")

    resp = client.post(
        "/api/dashboard/form-fill/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"instruction": "Use legal name"},
        files={"file": _pdf_upload()},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "fields": [
            {
                "field_name": "full_name",
                "field_type": "Text",
                "field_label": "Student Name",
                "field_context": "Full legal name of the student",
                "page": 0,
                "proposed_value": "Alice Example",
                "confidence": "high",
                "source": "profile",
            }
        ],
        "form_field_count": 1,
        "filled_count": 1,
        "unfilled_count": 0,
    }


def test_legacy_generate_route_still_works(client, monkeypatch):
    monkeypatch.setattr(form_fill_mod, "fill_pdf_fields", lambda _pdf_bytes, _values: b"filled-pdf")

    token = _auth_token(client, "form-fill-generate@example.com")

    resp = client.post(
        "/api/dashboard/form-fill/generate",
        headers={"Authorization": f"Bearer {token}"},
        data={"values": "{\"full_name\":\"Alice Example\"}"},
        files={"file": _pdf_upload()},
    )

    assert resp.status_code == 200
    assert resp.content == b"filled-pdf"
    assert resp.headers["content-type"] == "application/pdf"
