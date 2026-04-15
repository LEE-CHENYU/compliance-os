"""Test database initialization and table creation."""

import os
import tempfile

import pytest
from sqlalchemy import inspect

import compliance_os.web.models.database as database_mod
from compliance_os.web.models.database import configured_database_url, create_engine_and_tables, get_session


def test_tables_created():
    """All four tables exist after init."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        os.environ["COPILOT_DB_PATH"] = db_path
        engine = create_engine_and_tables(db_path)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "cases" in tables
        assert "discovery_answers" in tables
        assert "chat_messages" in tables
        assert "documents" in tables
        del os.environ["COPILOT_DB_PATH"]


def test_session_creates_and_queries():
    """Session can insert and query a case."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        engine = create_engine_and_tables(db_path)
        from compliance_os.web.models.tables import CaseRow
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            case = CaseRow(workflow_type="tax", status="discovery")
            session.add(case)
            session.commit()
            assert case.id is not None
            assert case.status == "discovery"


def test_configured_database_url_uses_database_url_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com/guardian?sslmode=require")

    url = configured_database_url()

    assert url == "postgresql+psycopg://user:pass@db.example.com/guardian?sslmode=require"


def test_configured_database_url_prefers_explicit_sqlite_path(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com/guardian")

    url = configured_database_url("/tmp/test.db")

    assert url == "sqlite:////tmp/test.db"


def test_configured_database_url_accepts_explicit_postgres_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    url = configured_database_url("postgresql://user:pass@db.example.com/guardian?sslmode=require")

    assert url == "postgresql+psycopg://user:pass@db.example.com/guardian?sslmode=require"


def test_create_engine_and_tables_uses_pool_pre_ping_for_postgres(monkeypatch):
    captured: dict[str, object] = {}

    class DummyEngine:
        dialect = type("Dialect", (), {"name": "postgresql"})()

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com/guardian")
    monkeypatch.setattr(database_mod.Base.metadata, "create_all", lambda engine: None)
    monkeypatch.setattr(
        "compliance_os.web.models.tables_v2.Base.metadata.create_all",
        lambda engine: None,
    )
    monkeypatch.setattr(database_mod, "_ensure_v2_columns", lambda engine: None)
    monkeypatch.setattr(database_mod, "_ensure_marketplace_columns", lambda engine: None)
    monkeypatch.setattr(database_mod, "_ensure_auth_columns", lambda engine: None)

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyEngine()

    monkeypatch.setattr(database_mod, "create_engine", fake_create_engine)

    create_engine_and_tables()

    assert captured["url"] == "postgresql+psycopg://user:pass@db.example.com/guardian"
    assert captured["kwargs"]["pool_pre_ping"] is True
    assert "connect_args" not in captured["kwargs"]
