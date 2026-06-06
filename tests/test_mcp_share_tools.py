import importlib
import json

import pytest


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    import compliance_os.consent as consent
    importlib.reload(consent)
    yield
    database._engine = None
    database._SessionLocal = None


def test_share_tool_gates_then_management(local_env, monkeypatch):
    from compliance_os import local_engine, mcp_server

    monkeypatch.setattr(local_engine, "_post_context_share",
                        lambda b, p, t: {"reference_id": "ref-9", "purpose": p})

    out = json.loads(mcp_server.share_data_room("lawyer-matching"))
    assert out["status"] == "consent_required"

    out2 = json.loads(mcp_server.share_data_room("lawyer-matching", confirm=True, remember="always"))
    assert out2["status"] == "shared"

    listed = json.loads(mcp_server.list_egress_consents())
    assert any(c["purpose"] == "lawyer-matching" for c in listed["consents"])

    revoked = json.loads(mcp_server.revoke_egress_consent("lawyer-matching"))
    assert revoked["revoked"] == "lawyer-matching"
    listed2 = json.loads(mcp_server.list_egress_consents())
    assert all(c["purpose"] != "lawyer-matching" for c in listed2["consents"])
