"""Tests for the License / Entitlements Control Plane (Plan 3 of 4)."""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


def _make_user_with_token(db):
    import secrets as _secrets
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.services.auth_service import issue_openclaw_token

    user = UserRow(email=f"u{_secrets.token_hex(4)}@x.com", password_hash="x", role="user")
    db.add(user)
    db.commit()
    _row, raw = issue_openclaw_token(user, db)
    db.commit()
    return user, raw


def test_validate_known_key_returns_active_free(local_db):
    from compliance_os.web.routers.license import ValidateRequest, validate

    db = next(local_db.get_session())
    try:
        _user, key = _make_user_with_token(db)
        out = validate(ValidateRequest(license_key=key, ext_version="2.0.0"), db=db)
        assert out["valid"] is True
        assert out["status"] == "active"
        assert out["tier"] == "free"
        assert "extraction" in out["features"]
        assert out["grace_until"]  # an ISO timestamp
    finally:
        db.close()


def test_validate_bad_key_is_invalid(local_db):
    from compliance_os.web.routers.license import ValidateRequest, validate

    db = next(local_db.get_session())
    try:
        out = validate(ValidateRequest(license_key="gdn_oc_dead_beef"), db=db)
        assert out["valid"] is False
        assert out["status"] == "invalid"
        assert out["features"] == []
    finally:
        db.close()


def test_license_route_is_registered():
    from compliance_os.web.app import app

    paths = {r.path for r in app.routes}
    assert "/api/license/validate" in paths
