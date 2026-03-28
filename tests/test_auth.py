"""Tests for auth endpoints."""
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from compliance_os.web.app import app
from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables_v2 import Base as BaseV2


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from compliance_os.web.models.database import Base as OldBase
    OldBase.metadata.create_all(engine)
    BaseV2.metadata.create_all(engine)
    # Also create auth tables (UserRow uses same Base)
    from compliance_os.web.models.auth import UserRow  # noqa: F401
    BaseV2.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)

    def override():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_register(client):
    resp = client.post("/api/auth/register", json={"email": "test@example.com", "password": "secure123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["email"] == "test@example.com"


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    resp = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass456"})
    assert resp.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "wrong@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "badpass"})
    assert resp.status_code == 401


def test_me_with_token(client):
    resp = client.post("/api/auth/register", json={"email": "me@example.com", "password": "pass123"})
    token = resp.json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_link_check(client):
    # Register
    resp = client.post("/api/auth/register", json={"email": "link@example.com", "password": "pass123"})
    token = resp.json()["token"]
    # Create a check
    resp = client.post("/api/checks", json={"track": "stem_opt", "answers": {}})
    check_id = resp.json()["id"]
    # Link it
    resp = client.post(f"/api/auth/link-check/{check_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # Verify
    resp = client.get(f"/api/checks/{check_id}")
    assert resp.json()["answers"] is not None  # check still accessible


def test_google_auth_url_uses_request_origin_when_redirect_uri_not_configured(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)

    resp = client.get(
        "/api/auth/google/url",
        headers={
            "host": "guardiancompliance.app",
            "x-forwarded-proto": "https",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    query = parse_qs(urlparse(data["url"]).query)
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == ["https://guardiancompliance.app/api/auth/google/callback"]


def test_google_callback_redirects_to_request_origin_when_frontend_url_not_configured(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    import httpx
    import jwt

    def fake_post(url, data):
        assert url == "https://oauth2.googleapis.com/token"
        assert data["redirect_uri"] == "https://guardiancompliance.app/api/auth/google/callback"
        return SimpleNamespace(status_code=200, json=lambda: {"id_token": "fake-id-token"})

    def fake_decode(token, options):
        assert token == "fake-id-token"
        return {"email": "oauth@example.com"}

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(jwt, "decode", fake_decode)

    resp = client.get(
        "/api/auth/google/callback?code=test-code",
        headers={
            "host": "guardiancompliance.app",
            "x-forwarded-proto": "https",
        },
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert location.startswith("https://guardiancompliance.app/login?token=")
    assert "email=oauth@example.com" in location


def test_google_callback_redirects_to_local_frontend_when_running_locally(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    import httpx
    import jwt

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, data: SimpleNamespace(status_code=200, json=lambda: {"id_token": "fake-id-token"}),
    )
    monkeypatch.setattr(jwt, "decode", lambda token, options: {"email": "local-oauth@example.com"})

    resp = client.get(
        "/api/auth/google/callback?code=test-code",
        headers={"host": "localhost:8000"},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith("http://localhost:3000/login?token=")
