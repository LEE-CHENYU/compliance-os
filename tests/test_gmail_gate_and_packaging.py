"""Tests for Gmail gating (Task 1) and .dxt v2 packaging (Task 2).

Task 1: when Guardian's own Gmail OAuth isn't configured, the 6 Gmail tools
must return a redirect message rather than hanging on get_service()'s
browser OAuth flow.

Task 2: the MANIFEST in scripts/build_dxt.py must be v2.0.0 local-first:
GUARDIAN_LICENSE_KEY + GUARDIAN_MODE=local, single license_key user_config,
no openai_api_key / api_url / token.
"""

import importlib.util
import json
import pathlib

import pytest


# ---------------------------------------------------------------------------
# Task 1: Gmail gating
# ---------------------------------------------------------------------------


def test_is_gmail_configured_reflects_files(monkeypatch, tmp_path):
    from compliance_os import gmail_client

    monkeypatch.setattr(gmail_client, "CREDENTIALS_PATH", tmp_path / "gmail_credentials.json")
    monkeypatch.setattr(gmail_client, "TOKEN_PATH", tmp_path / "gmail_token.json")
    assert gmail_client.is_gmail_configured() is False

    (tmp_path / "gmail_token.json").write_text("{}")
    assert gmail_client.is_gmail_configured() is True


def test_gmail_search_redirects_when_unconfigured(monkeypatch):
    from compliance_os import gmail_client, mcp_server

    monkeypatch.setattr(gmail_client, "is_gmail_configured", lambda: False)
    out = json.loads(mcp_server.gmail_search("is:unread"))
    assert out["error"] == "gmail_not_configured"
    assert "connector" in out["message"]


def test_gmail_send_redirects_when_unconfigured(monkeypatch):
    from compliance_os import gmail_client, mcp_server

    monkeypatch.setattr(gmail_client, "is_gmail_configured", lambda: False)
    out = json.loads(mcp_server.gmail_send("draft_123"))
    assert out["error"] == "gmail_not_configured"


# ---------------------------------------------------------------------------
# Task 2: .dxt v2 manifest
# ---------------------------------------------------------------------------


def _load_build_dxt():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "build_dxt.py"
    spec = importlib.util.spec_from_file_location("build_dxt", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: build() runs only under __main__
    return mod


def test_dxt_manifest_is_v2_local_first():
    m = _load_build_dxt().MANIFEST
    assert m["version"].startswith("2.")
    env = m["server"]["mcp_config"]["env"]
    assert env.get("GUARDIAN_MODE") == "local"
    assert "GUARDIAN_LICENSE_KEY" in env
    # hosted/cloud knobs are gone
    assert "OPENAI_API_KEY" not in env
    assert "GUARDIAN_API_URL" not in env
    assert "GUARDIAN_TOKEN" not in env


def test_dxt_user_config_is_single_license_key():
    m = _load_build_dxt().MANIFEST
    uc = m["user_config"]
    assert set(uc) == {"license_key"}
    assert uc["license_key"]["required"] is True
    assert uc["license_key"]["sensitive"] is True
