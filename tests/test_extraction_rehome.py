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


def test_local_upload_document_stores_and_returns_schema(local_db):
    from compliance_os import local_engine

    # A plain-text "I-20" so OCR is a trivial local read (no PDF fixture needed).
    src = Path(os.environ["GUARDIAN_HOME"]) / "sample_i20.txt"
    src.write_text("SEVIS ID: N0001234567\nSchool: Test University\n")

    result = local_engine.local_upload_document(str(src), doc_type="i20")
    assert "doc_id" in result and result["doc_type"] == "i20"
    assert "N0001234567" in result["text"]
    # the schema for this doc type rides along so Claude knows what to extract
    assert any(e["fact_key"] == "sevis_id" for e in result["extraction_schema"])

    # File was copied into the local data dir, and NO facts exist yet
    # (extraction is Claude's job, not the upload's).
    facts = local_engine.local_get_facts()
    assert facts["facts"] == []


def test_mcp_upload_document_uses_local_path(local_db):
    from compliance_os import mcp_server

    src = Path(os.environ["GUARDIAN_HOME"]) / "doc.txt"
    src.write_text("SEVIS ID: N0009999999\n")
    out = json.loads(mcp_server.upload_document(str(src), doc_type="i20"))
    assert out["doc_type"] == "i20" and "doc_id" in out


def test_record_extracted_facts_projects_to_sot(local_db):
    from compliance_os import local_engine

    src = Path(os.environ["GUARDIAN_HOME"]) / "i20.txt"
    src.write_text("SEVIS ID: N0001234567\n")
    up = local_engine.local_upload_document(str(src), doc_type="i20")
    doc_id = up["doc_id"]

    result = local_engine.local_record_extracted_facts(
        doc_id,
        [{"field_name": "sevis_number", "value": "N0001234567", "confidence": 0.95}],
    )
    assert "sevis_number" in result["recorded_fields"]

    # The deterministic projection mapped (i20, sevis_number) -> sevis_id in the SoT.
    facts = {f["fact_key"]: f["value"] for f in local_engine.local_get_facts()["facts"]}
    assert "sevis_id" in facts


def test_record_extracted_facts_unknown_doc_returns_error(local_db):
    from compliance_os import local_engine

    out = local_engine.local_record_extracted_facts("no-such-id", [])
    assert "error" in out


def test_mcp_record_extracted_facts_tool(local_db):
    from compliance_os import local_engine, mcp_server

    src = Path(os.environ["GUARDIAN_HOME"]) / "i20b.txt"
    src.write_text("SEVIS ID: N0002223333\n")
    doc_id = local_engine.local_upload_document(str(src), doc_type="i20")["doc_id"]
    out = json.loads(
        mcp_server.record_extracted_facts(
            doc_id, [{"field_name": "sevis_number", "value": "N0002223333"}]
        )
    )
    assert "sevis_number" in out["recorded_fields"]


def test_local_ask_grounding_returns_context_and_refs(local_db):
    from compliance_os import local_engine

    src = Path(os.environ["GUARDIAN_HOME"]) / "i20c.txt"
    src.write_text("SEVIS ID: N0007778888\nSchool: Grounding University\n")
    doc_id = local_engine.local_upload_document(str(src), doc_type="i20")["doc_id"]
    local_engine.local_record_extracted_facts(
        doc_id, [{"field_name": "sevis_number", "value": "N0007778888"}]
    )

    out = local_engine.local_ask_grounding("what is my sevis id")
    assert set(out) >= {"question", "context", "references"}
    assert isinstance(out["context"], str)
    assert isinstance(out["references"], list)


def test_mcp_guardian_ask_local_returns_grounding(local_db):
    import asyncio
    from compliance_os import mcp_server

    def _run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(asyncio.new_event_loop())

    out = json.loads(_run(mcp_server.guardian_ask("what documents do I have")))
    assert "context" in out and "references" in out
