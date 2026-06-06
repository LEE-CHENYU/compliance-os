import io
import secrets
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    database.get_engine()  # creates engine + all tables (incl. shared_context)
    from compliance_os.web.app import app
    return TestClient(app)


def _make_user_and_token():
    # Reuse the project's auth: create a user + a valid bearer (JWT) token.
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.models.database import get_session
    from compliance_os.web.services.auth_service import create_token
    db = next(get_session())
    try:
        user = UserRow(
            email=f"t-{secrets.token_hex(4)}@example.com",
            password_hash=secrets.token_hex(16),
            role="user",
        )
        db.add(user)
        db.commit()
        token = create_token(user.id, user.email)
        return user.id, token
    finally:
        db.close()


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", "{}")
    return buf.getvalue()


def test_share_requires_auth(client):
    r = client.post("/api/context/share", data={"purpose": "lawyer-matching"},
                    files={"file": ("d.zip", _zip_bytes(), "application/zip")})
    assert r.status_code == 401


def test_share_stores_blob_and_row(client):
    uid, token = _make_user_and_token()
    r = client.post(
        "/api/context/share",
        headers={"Authorization": f"Bearer {token}"},
        data={"purpose": "lawyer-matching"},
        files={"file": ("d.zip", _zip_bytes(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["purpose"] == "lawyer-matching" and body["reference_id"]

    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.tables_v2 import SharedContextRow
    db = next(get_session())
    try:
        row = db.query(SharedContextRow).filter(SharedContextRow.user_id == uid).first()
        assert row is not None and row.purpose == "lawyer-matching"
        from pathlib import Path
        assert Path(row.path).exists()
    finally:
        db.close()
