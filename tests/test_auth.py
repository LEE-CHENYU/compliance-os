"""Tests for auth endpoints."""
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
