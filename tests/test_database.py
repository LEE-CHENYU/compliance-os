"""Test database initialization and table creation."""

import os
import tempfile

import pytest
from sqlalchemy import inspect

from compliance_os.web.models.database import create_engine_and_tables, get_session


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
