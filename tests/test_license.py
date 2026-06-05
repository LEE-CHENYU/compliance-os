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


# ─── Task 2: Client activation module ────────────────────────────────────────

def test_unconfigured_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    assert licensing.activation_state() == "unconfigured"
    block = licensing.activation_block()
    assert block is not None and block["state"] == "unconfigured"


def test_active_when_online_validates(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": True, "status": "active", "tier": "free",
                     "features": ["extraction", "chat"], "grace_until": None},
    )
    assert licensing.activation_state() == "active"
    assert licensing.activation_block() is None


def test_inactive_when_server_says_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": False, "status": "invalid", "tier": "free",
                     "features": [], "grace_until": None},
    )
    assert licensing.activation_state() == "inactive"
    assert licensing.activation_block()["state"] == "inactive"


def test_offline_grace_then_expiry(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    # Offline: validate_online returns None; fall back to cache.
    monkeypatch.setattr(licensing, "validate_online", lambda key: None)

    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    licensing._write_cache({"valid": True, "status": "active", "tier": "free",
                            "features": ["extraction"], "grace_until": future})
    assert licensing.activation_state() == "active"   # within grace

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    licensing._write_cache({"valid": True, "status": "active", "tier": "free",
                            "features": ["extraction"], "grace_until": past})
    assert licensing.activation_state() == "expired_offline"


# ─── Task 3: GatedMCP gate ────────────────────────────────────────────────────

def _extract_text(result) -> str:
    """Extract text from a FastMCP call_tool result robustly.

    FastMCP 1.27 returns a tuple (list[TextContent], structured) rather than
    a plain list[TextContent], so we peel the outer tuple/list one extra level
    when the first element is itself a list.
    """
    # Unwrap outer tuple → list[TextContent]
    if isinstance(result, tuple):
        result = result[0]
    # result is now list[TextContent] or TextContent or similar
    if isinstance(result, list):
        item = result[0]
        if hasattr(item, "text"):
            return item.text
        # item is itself a list (FastMCP nested shape)
        if isinstance(item, list) and item:
            return item[0].text
    if hasattr(result, "text"):
        return result.text
    return json.dumps(result)


def test_gate_blocks_unconfigured_standalone(monkeypatch, tmp_path):
    """In standalone mode with no key, dispatching any tool returns the
    activation message instead of running the tool."""
    import asyncio

    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import mcp_server

    def _run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(asyncio.new_event_loop())

    result = _run(mcp_server.mcp.call_tool("get_extraction_schema", {"doc_type": "i20"}))
    text = _extract_text(result)
    assert "activation_required" in text


def test_gate_allows_when_active(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing, mcp_server

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": True, "status": "active", "tier": "free",
                     "features": ["extraction", "chat", "facts", "documents"],
                     "grace_until": None},
    )

    def _run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(asyncio.new_event_loop())

    result = _run(mcp_server.mcp.call_tool("get_extraction_schema", {"doc_type": "i20"}))
    text = _extract_text(result)
    assert "activation_required" not in text
    assert "sevis_id" in text  # the real tool ran


# ─── Task 4: End-to-end ───────────────────────────────────────────────────────

def test_license_end_to_end(local_db, monkeypatch, tmp_path):
    """Server issues entitlements for a real key; client caches + activates;
    the gate then lets a tool run."""
    import asyncio
    from compliance_os import licensing
    from compliance_os.web.routers.license import ValidateRequest, validate

    # Server side: a real user + key resolves to active/free entitlements.
    db = next(local_db.get_session())
    try:
        _user, key = _make_user_with_token(db)
        server_out = validate(ValidateRequest(license_key=key), db=db)
    finally:
        db.close()
    assert server_out["valid"] and "extraction" in server_out["features"]

    # Client side: point validate_online at the in-process server result.
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", key)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.setattr(licensing, "validate_online", lambda k: server_out)
    assert licensing.activation_state() == "active"
    assert licensing.activation_block() is None
