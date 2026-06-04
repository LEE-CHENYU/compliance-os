# tests/test_local_engine.py
# Module import header — all tests in this file rely on these.
import asyncio
import os
from pathlib import Path

import pytest


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
