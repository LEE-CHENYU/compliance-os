"""Publishing the data room to a share URL: the /api/context/publish-dataroom
endpoint (extract zip server-side, mint share token, return URL rendered by
the existing /share/[token] page) and the consent-gated MCP tool."""

import io
import json
import secrets
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    database.get_engine()
    from compliance_os.web.app import app
    return TestClient(app)


def _make_user_and_token():
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


def _zip_bytes(members: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in (members or {"manifest.json": "{}", "immigration/i20/i20.txt": "SEVIS"}).items():
            zf.writestr(name, text)
    return buf.getvalue()


def test_publish_requires_auth(client):
    r = client.post("/api/context/publish-dataroom",
                    data={"template_id": "h1b_petition"},
                    files={"file": ("d.zip", _zip_bytes(), "application/zip")})
    assert r.status_code == 401


def test_publish_happy_path_returns_share_url(client):
    uid, token = _make_user_and_token()
    r = client.post(
        "/api/context/publish-dataroom",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_id": "h1b_petition", "recipient": "Attorney Kim", "expires_in_days": "7"},
        files={"file": ("d.zip", _zip_bytes(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "/share/" in body["url"]
    assert body["files"] == 2 and body["expires_in_days"] == 7

    # the minted token decodes, points at an existing extracted folder, and
    # the share API itself can resolve it (the existing webpage's data source)
    from compliance_os.web.services.share_tokens import decode_share_token
    payload = decode_share_token(body["token"])
    assert payload["template_id"] == "h1b_petition"
    assert payload["recipient"] == "Attorney Kim"
    assert Path(payload["folder"]).is_dir()
    assert (Path(payload["folder"]) / "immigration/i20/i20.txt").exists()

    share = client.get(f"/api/share/{body['token']}")
    assert share.status_code == 200, share.text
    assert share.json()["template_id"] == "h1b_petition"


def test_publish_accepts_all_registry_templates(client):
    uid, token = _make_user_and_token()
    r = client.post(
        "/api/context/publish-dataroom",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_id": "founder_h1b"},
        files={"file": ("d.zip", _zip_bytes(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    share = client.get(f"/api/share/{r.json()['token']}")
    assert share.status_code == 200  # registry swap: founder_h1b renders too


def test_publish_rejects_unknown_template(client):
    uid, token = _make_user_and_token()
    r = client.post(
        "/api/context/publish-dataroom",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_id": "not_a_template"},
        files={"file": ("d.zip", _zip_bytes(), "application/zip")},
    )
    assert r.status_code == 400


def test_publish_rejects_zip_slip(client):
    uid, token = _make_user_and_token()
    evil = _zip_bytes({"../../evil.txt": "pwned"})
    r = client.post(
        "/api/context/publish-dataroom",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_id": "h1b_petition"},
        files={"file": ("d.zip", evil, "application/zip")},
    )
    assert r.status_code == 400
    assert "unsafe path" in r.text


def test_publish_rejects_non_zip(client):
    uid, token = _make_user_and_token()
    r = client.post(
        "/api/context/publish-dataroom",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_id": "h1b_petition"},
        files={"file": ("d.zip", b"not a zip", "application/zip")},
    )
    assert r.status_code == 400


# ── the MCP tool (consent flow + card) ─────────────────────────────

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


def test_publish_tool_requires_consent_first(local_db):
    from compliance_os import mcp_server
    out = json.loads(mcp_server.publish_data_room())
    assert out["status"] == "consent_required"
    assert "Nothing is sent unless you approve" in out["message"]


def test_publish_tool_returns_url_card_after_consent(local_db, monkeypatch):
    from compliance_os import local_engine, mcp_server
    # no real network: stub the cloud POST
    monkeypatch.setattr(
        local_engine, "_post_publish_dataroom",
        lambda zip_bytes, template_id, recipient, days, token: {
            "url": "https://guardiancompliance.app/share/FAKE", "reference_id": "ref-1",
            "expires_in_days": days,
        },
    )
    card = mcp_server.publish_data_room(confirm=True, remember="once")
    assert "Data room published" in card
    assert "https://guardiancompliance.app/share/FAKE" in card
    assert "read-only" in card


def test_zip_dir_roundtrip(tmp_path):
    from compliance_os.local_engine import _zip_dir
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.txt").write_text("hello")
    (tmp_path / "top.txt").write_text("hi")
    data = _zip_dir(tmp_path)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert sorted(zf.namelist()) == ["a/x.txt", "top.txt"]
