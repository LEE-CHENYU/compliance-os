# tests/test_local_engine.py
# Module import header — all tests in this file rely on these.
import asyncio
import os
from pathlib import Path

import pytest


def _run_async(coro):
    """Run a coroutine without leaving the global event loop closed/None.

    asyncio.run() calls set_event_loop(None) on exit, which breaks tests that
    rely on asyncio.get_event_loop() (e.g. tests/test_mcp_server.py). Installing
    a fresh open loop afterward keeps the suite order-independent.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


def test_local_mode_db_url_points_at_guardian_home(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # configured_database_url() reads env live, so no module reload is needed.
    from compliance_os.web.models import database

    url = database.configured_database_url()
    assert url == f"sqlite:///{tmp_path / 'guardian.db'}"


def test_hosted_mode_db_url_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "hosted")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from compliance_os.web.models import database

    url = database.configured_database_url()
    assert url.endswith("copilot.db")


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    """Fresh local SQLite engine rooted at a temp ~/.guardian.

    No module reload: we reset the lazily-cached globals so the next
    get_engine()/get_session() rebuilds against the temp guardian.db.
    Resetting (not reloading) keeps local_engine's imported get_session
    pointing at the same function object whose globals we reset.
    """
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


def test_is_local_mode_reads_env(monkeypatch):
    from compliance_os import local_engine
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    assert local_engine.is_local_mode() is True
    monkeypatch.setenv("GUARDIAN_MODE", "hosted")
    assert local_engine.is_local_mode() is False
    monkeypatch.delenv("GUARDIAN_MODE", raising=False)
    assert local_engine.is_local_mode() is False


def test_get_local_user_id_is_stable_and_singleton(local_db):
    from compliance_os import local_engine
    db = next(local_db.get_session())
    try:
        id1 = local_engine.get_local_user_id(db)
        id2 = local_engine.get_local_user_id(db)
        assert id1 == id2
        from compliance_os.web.models.auth import UserRow
        assert db.query(UserRow).count() == 1
    finally:
        db.close()


def test_local_facts_shape_matches_hosted_router_shape(local_db):
    """The local adapter and the hosted router must emit the same envelope:
    GET → {"facts": [...]}, POST → {"fact": {...}, "superseded": ...}."""
    from compliance_os import local_engine

    set_out = local_engine.local_set_fact("country_of_citizenship", "India")
    assert set(set_out) == {"fact", "superseded"}

    get_out = local_engine.local_get_facts(category="personal")
    assert set(get_out) == {"facts"}
    assert all(set(f) >= {"fact_key", "value", "source_type"} for f in get_out["facts"])

    # Conflict resolution envelope
    fact_id = set_out["fact"]["id"]
    resolved = local_engine.local_resolve_conflict(fact_id, "keep_current")
    assert set(resolved) == {"fact"}


def test_force_local_embeddings_sets_provider(monkeypatch):
    from compliance_os import local_engine
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-be-ignored")
    monkeypatch.delenv("GUARDIAN_EMBEDDING_PROVIDER", raising=False)

    local_engine.force_local_embeddings()
    assert os.environ["GUARDIAN_EMBEDDING_PROVIDER"] == "local"


def test_mcp_get_user_facts_uses_local_path(local_db):
    from compliance_os import local_engine, mcp_server

    # Seed via the local adapter
    local_engine.local_set_fact("sevis_id", "N0001234567")

    # The MCP tool (async) must return the seeded fact without any HTTP
    result = _run_async(mcp_server.get_user_facts())
    import json
    payload = json.loads(result)
    keys = {f["fact_key"] for f in payload["facts"]}
    assert "sevis_id" in keys


def test_local_set_then_get_roundtrips(local_db):
    from compliance_os import local_engine

    set_out = local_engine.local_set_fact(
        "current_annual_salary", "135000", notes="locked in test",
    )
    assert set_out["fact"]["fact_key"] == "current_annual_salary"
    assert set_out["fact"]["source_type"] == "decision_lock"
    assert set_out["superseded"] is None

    get_out = local_engine.local_get_facts()
    keys = {f["fact_key"] for f in get_out["facts"]}
    assert "current_annual_salary" in keys


def test_local_set_fact_supersedes_previous(local_db):
    from compliance_os import local_engine

    local_engine.local_set_fact("current_employer_legal_name", "Acme Inc")
    second = local_engine.local_set_fact("current_employer_legal_name", "Beta LLC")
    assert second["superseded"] is not None
    assert second["superseded"]["value"] != second["fact"]["value"]


def test_serialize_fact_matches_router_contract(local_db):
    from compliance_os.web.services.user_facts import serialize_fact, upsert_fact
    from compliance_os import local_engine

    db = next(local_db.get_session())
    try:
        user_id = local_engine.get_local_user_id(db)
        row, _ = upsert_fact(
            db, user_id=user_id, fact_key="legal_name", value="Jane Q",
            source_type="decision_lock", source_ref={"ui_path": "test"},
        )
        db.commit()
        out = serialize_fact(row)
        assert set(out) == {
            "id", "fact_key", "label", "category", "track", "value",
            "notes", "source_type", "source_ref", "locked_at", "is_active",
            "superseded_by_id", "detected_conflicts", "created_at", "updated_at",
        }
        assert out["fact_key"] == "legal_name"
        assert out["detected_conflicts"] == []
    finally:
        db.close()
