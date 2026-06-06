import importlib

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


def test_share_requires_consent_then_uploads(local_env, monkeypatch):
    from compliance_os import local_engine

    posted = {}
    def fake_post(zip_bytes, purpose, token):
        posted["bytes"] = zip_bytes
        posted["purpose"] = purpose
        return {"reference_id": "ref-123", "purpose": purpose}
    monkeypatch.setattr(local_engine, "_post_context_share", fake_post)

    # No prior consent, no confirm -> a consent request, nothing posted.
    res = local_engine.local_share_data_room("lawyer-matching", confirm=False, remember="once")
    assert res["status"] == "consent_required"
    assert "lawyer-matching" in res["purpose"]
    assert "bytes" not in posted

    # Confirm -> exactly one upload, reference returned.
    res2 = local_engine.local_share_data_room("lawyer-matching", confirm=True, remember="always")
    assert res2["status"] == "shared"
    assert res2["reference_id"] == "ref-123"
    assert posted["purpose"] == "lawyer-matching"
    assert isinstance(posted["bytes"], (bytes, bytearray)) and len(posted["bytes"]) > 0

    # Always grant recorded -> a later call proceeds without a request.
    posted.clear()
    res3 = local_engine.local_share_data_room("lawyer-matching", confirm=False, remember="once")
    assert res3["status"] == "shared"
    assert posted["purpose"] == "lawyer-matching"


def test_share_errors_when_server_returns_no_reference(local_env, monkeypatch):
    from compliance_os import local_engine
    monkeypatch.setattr(local_engine, "_post_context_share",
                        lambda b, p, t: (_ for _ in ()).throw(RuntimeError("context/share returned no reference_id: {}")))
    import pytest
    with pytest.raises(RuntimeError):
        local_engine.local_share_data_room("lawyer-matching", confirm=True, remember="once")
