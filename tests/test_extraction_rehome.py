# tests/test_extraction_rehome.py
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    """Fresh local SQLite engine rooted at a temp ~/.guardian (mirrors test_local_engine)."""
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.setenv("GUARDIAN_DATA_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


def test_schema_for_doc_type_i20_lists_sevis_id():
    from compliance_os.facts.extraction_map import schema_for_doc_type

    schema = schema_for_doc_type("i20")
    by_field = {e["source_field"]: e for e in schema}
    assert "sevis_number" in by_field
    assert by_field["sevis_number"]["fact_key"] == "sevis_id"
    # enriched from the vocabulary
    assert "label" in by_field["sevis_number"]
    assert "shape" in by_field["sevis_number"]


def test_schema_for_unknown_doc_type_is_empty():
    from compliance_os.facts.extraction_map import schema_for_doc_type

    assert schema_for_doc_type("not_a_doc_type") == []


def test_get_extraction_schema_tool_returns_json():
    from compliance_os import mcp_server

    out = json.loads(mcp_server.get_extraction_schema("i20"))
    assert any(e["fact_key"] == "sevis_id" for e in out)
