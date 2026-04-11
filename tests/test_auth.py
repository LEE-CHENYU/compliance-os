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
from compliance_os.web.models.marketplace import MarketplaceUserRow
from compliance_os.web.models.tables_v2 import Base as BaseV2, CheckRow


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
    assert data["role"] == "user"


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
    assert resp.json()["role"] == "user"


def test_signup_alias_creates_marketplace_user(client):
    resp = client.post("/api/auth/signup", json={"email": "marketplace-user@example.com", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "marketplace-user@example.com"
    assert data["role"] == "user"

    session = next(app.dependency_overrides[get_session]())
    try:
        marketplace_user = (
            session.query(MarketplaceUserRow)
            .filter(MarketplaceUserRow.email == "marketplace-user@example.com")
            .first()
        )
        assert marketplace_user is not None
        assert marketplace_user.role == "user"
    finally:
        session.close()


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


def test_google_auth_url_includes_safe_next_path_in_state(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)

    resp = client.get("/api/auth/google/url?next=/form-8843/success%3ForderId%3Dabc%26download%3D1")

    assert resp.status_code == 200
    query = parse_qs(urlparse(resp.json()["url"]).query)
    assert query["state"] == ["/form-8843/success?orderId=abc&download=1"]


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
    assert "email=oauth%40example.com" in location


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


def test_google_callback_preserves_safe_next_path(client, monkeypatch):
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
    monkeypatch.setattr(jwt, "decode", lambda token, options: {"email": "next-path@example.com"})

    resp = client.get(
        "/api/auth/google/callback?code=test-code&state=/form-8843/success%3ForderId%3Dabc%26download%3D1",
        headers={"host": "localhost:8000"},
        follow_redirects=False,
    )

    assert resp.status_code in (302, 307)
    location = urlparse(resp.headers["location"])
    query = parse_qs(location.query)
    assert query["next"] == ["/form-8843/success?orderId=abc&download=1"]


def test_openclaw_connection_issues_scoped_token(client):
    resp = client.post("/api/auth/register", json={"email": "openclaw@example.com", "password": "pass123"})
    jwt_token = resp.json()["token"]

    connection = client.get(
        "/api/auth/openclaw/connection",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert connection.status_code == 200
    assert connection.json()["active_token"] is None

    issued = client.post(
        "/api/auth/openclaw/token",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    assert issued.status_code == 200
    data = issued.json()
    assert data["token"].startswith("gdn_oc_")
    assert data["scope"] == "openclaw"
    assert data["active_token"]["token_prefix"]


def test_openclaw_connection_defaults_to_https_for_non_local_hosts(client):
    resp = client.post("/api/auth/register", json={"email": "openclaw-https@example.com", "password": "pass123"})
    jwt_token = resp.json()["token"]

    connection = client.get(
        "/api/auth/openclaw/connection",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "host": "guardiancompliance.app",
        },
    )

    assert connection.status_code == 200
    assert connection.json()["api_url"] == "https://guardiancompliance.app"


def test_openclaw_token_can_access_dashboard_but_not_jwt_only_auth_routes(client):
    resp = client.post("/api/auth/register", json={"email": "openclaw-dashboard@example.com", "password": "pass123"})
    jwt_token = resp.json()["token"]
    user_id = resp.json()["user_id"]

    session = next(app.dependency_overrides[get_session]())
    try:
        session.add(CheckRow(track="stem_opt", status="saved", user_id=user_id, answers={"stage": "stem_opt"}))
        session.commit()
    finally:
        session.close()

    issued = client.post(
        "/api/auth/openclaw/token",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    api_token = issued.json()["token"]

    stats = client.get(
        "/api/dashboard/stats",
        headers={"Authorization": f"Bearer {api_token}"},
    )
    assert stats.status_code == 200
    assert stats.json()["documents"] == 0

    forbidden = client.post(
        "/api/auth/link-check/nonexistent",
        headers={"Authorization": f"Bearer {api_token}"},
    )
    assert forbidden.status_code == 403


def test_openclaw_token_can_call_chat(client, monkeypatch):
    import compliance_os.web.routers.chat as chat_mod

    resp = client.post("/api/auth/register", json={"email": "openclaw-chat@example.com", "password": "pass123"})
    jwt_token = resp.json()["token"]

    issued = client.post(
        "/api/auth/openclaw/token",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    api_token = issued.json()["token"]

    monkeypatch.setattr(chat_mod, "chat_completion", lambda **kwargs: "Scoped token chat ok")

    resp = client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {api_token}"},
        json={"message": "status?", "history": []},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Scoped token chat ok"
