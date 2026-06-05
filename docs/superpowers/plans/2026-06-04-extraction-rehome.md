# Extraction Re-Home Implementation Plan (Plan 2 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In local mode, re-home the document→facts extraction loop so the user's Claude does the *perception* (reading values out of a document) while the local engine does the *bookkeeping* (storage, indexing, SoT projection, supersession, conflict detection) entirely in-process — no server LLM, no HTTP. Adds `get_extraction_schema`, a local-only `upload_document`, `record_extracted_facts`, and a no-model `guardian_ask` grounding bundle.

**Architecture:** Reuse the deterministic server internals directly: `register_uploaded_document` (versioning), `_upsert_extracted_field` → `_project_to_user_facts` (the full SoT projection with supersession + conflict detection), `extract_pdf_text_with_provenance` (local OCR), `retrieve_documents_for_query` via `_build_context` (local relational retrieval), and `DocumentIndexer` (local Chroma). The only thing removed is the server's `extract_document` LLM call — replaced by the user's Claude reading the parsed text against a schema and calling `record_extracted_facts`. Builds on Plan 1 (`compliance_os/local_engine.py`, `is_local_mode`, singleton local user).

**Tech Stack:** Python 3.11, SQLAlchemy (SQLite), FastMCP (`mcp`), ChromaDB/fastembed, pytest. No new dependencies.

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-04-local-first-compliance-loop-design.md` (§ "Extraction-Loop Redesign")
- `compliance_os/local_engine.py` — Plan 1 module being extended (`is_local_mode`, `get_local_user_id`, `get_session`, `serialize_fact`, `get_active_facts` already imported)
- `compliance_os/facts/extraction_map.py` — `EXTRACTION_TO_FACT_KEY: dict[tuple[str,str],str]`, `fact_key_for(doc_type, field_name)`
- `compliance_os/facts/vocabulary.py` — `resolve_fact_def(fact_key) -> FactDef|None`; `FactDef(label, category, track, typical_doc_types, shape)`
- `compliance_os/web/services/document_store.py` — `register_uploaded_document(check, row, content, source_path=None, *, db)`, `_upsert_extracted_field(db, *, doc, field_name, value, confidence, raw_text)` (writes `ExtractedFieldRow` AND projects to `user_facts`)
- `compliance_os/web/services/extractor.py` — `extract_pdf_text_with_provenance(file_path) -> TextExtractionResult(text, engine, metadata)`
- `compliance_os/web/routers/chat.py` — `_build_context(user_id, db, query=None) -> tuple[str, list[dict]]` (local retrieval, no LLM)
- `compliance_os/web/routers/dashboard.py:412` — the hosted `/upload` handler this mirrors (check→doc→register→extract)
- `compliance_os/web/models/tables_v2.py` — `CheckRow`, `DocumentRow`, `ExtractedFieldRow`
- `compliance_os/mcp_server.py` — tools `upload_document` (~665), `guardian_ask` (~502), `parse_document` (~534), `classify_document` (~575)

---

## File Structure

- **Modify** `compliance_os/facts/extraction_map.py` — add `schema_for_doc_type(doc_type)` (reverse lookup + vocabulary enrichment). Pure facts-domain logic; shared by hosted + local.
- **Modify** `compliance_os/local_engine.py` — add `_get_local_check`, `_local_ocr_text`, `local_upload_document`, `local_record_extracted_facts`, `local_ask_grounding`. The in-process extraction loop.
- **Modify** `compliance_os/mcp_server.py` — new tools `get_extraction_schema`, `record_extracted_facts`; local-mode branches in `upload_document` and `guardian_ask`.
- **Create** `tests/test_extraction_rehome.py` — unit + integration tests for the loop.

---

## Task 1: `schema_for_doc_type` + `get_extraction_schema` tool

**Files:**
- Modify: `compliance_os/facts/extraction_map.py` (append function)
- Modify: `compliance_os/mcp_server.py` (new tool)
- Test: `tests/test_extraction_rehome.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extraction_rehome.py::test_schema_for_doc_type_i20_lists_sevis_id -v`
Expected: FAIL — `ImportError: cannot import name 'schema_for_doc_type'`.

- [ ] **Step 3: Add `schema_for_doc_type` to `extraction_map.py`**

Append at the end of `compliance_os/facts/extraction_map.py` (after `fact_key_for`):

```python
def schema_for_doc_type(doc_type: str) -> list[dict]:
    """Return the SoT-tracked extraction targets for a document type.

    Reverse of EXTRACTION_TO_FACT_KEY, enriched with each fact's
    human label and value shape from the vocabulary. This is exactly
    what the extraction-schema tool hands the model: which fields to
    read out of this document, and where each lands in the SoT.
    """
    from compliance_os.facts.vocabulary import resolve_fact_def

    out: list[dict] = []
    for (dt, field_name), fact_key in EXTRACTION_TO_FACT_KEY.items():
        if dt != doc_type:
            continue
        fact_def = resolve_fact_def(fact_key)
        out.append(
            {
                "source_field": field_name,
                "fact_key": fact_key,
                "label": fact_def.label if fact_def else fact_key,
                "shape": fact_def.shape if fact_def else "string",
            }
        )
    out.sort(key=lambda e: e["source_field"])
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extraction_rehome.py::test_schema_for_doc_type_i20_lists_sevis_id tests/test_extraction_rehome.py::test_schema_for_unknown_doc_type_is_empty -v`
Expected: PASS (both).

- [ ] **Step 5: Add the `get_extraction_schema` MCP tool**

In `compliance_os/mcp_server.py`, near the other read-only tools (e.g. right after `classify_document`), add:

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="Get extraction schema",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def get_extraction_schema(doc_type: str) -> str:
    """List the fields to extract from a document of this type.

    Returns the SoT-tracked targets — each with the raw `source_field`
    to read, the canonical `fact_key` it maps to, a human `label`, and
    the value `shape` (string|number|date|object|list). After parsing a
    document, read these fields out of the text and submit them with
    record_extracted_facts. Runs locally with no token cost.

    Args:
        doc_type: The document type (e.g. "i20", "i797", "w2").
    """
    from compliance_os.facts.extraction_map import schema_for_doc_type

    return json.dumps(schema_for_doc_type(doc_type), indent=2)
```

- [ ] **Step 6: Test the tool + commit**

Add to `tests/test_extraction_rehome.py`:

```python
def test_get_extraction_schema_tool_returns_json():
    from compliance_os import mcp_server

    out = json.loads(mcp_server.get_extraction_schema("i20"))
    assert any(e["fact_key"] == "sevis_id" for e in out)
```

Run: `pytest tests/test_extraction_rehome.py -q`
Expected: PASS (3 tests).

```bash
git add compliance_os/facts/extraction_map.py compliance_os/mcp_server.py tests/test_extraction_rehome.py
git commit -m "feat(extract): schema_for_doc_type + get_extraction_schema MCP tool"
```

---

## Task 2: `local_upload_document` (store + index, no LLM) + wire `upload_document`

**Files:**
- Modify: `compliance_os/local_engine.py`
- Modify: `compliance_os/mcp_server.py` (`upload_document` local branch)
- Test: `tests/test_extraction_rehome.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extraction_rehome.py::test_local_upload_document_stores_and_returns_schema -v`
Expected: FAIL — `AttributeError: module 'compliance_os.local_engine' has no attribute 'local_upload_document'`.

- [ ] **Step 3: Add the upload helpers + function to `local_engine.py`**

Append to `compliance_os/local_engine.py`:

```python
def _get_local_check(db, user_id: str):
    """Find-or-create the singleton local 'check' that documents attach to.

    Mirrors dashboard._ensure_dashboard_check, replicated here so the
    local engine doesn't import the FastAPI router. One saved check per
    local user is enough for single-user local mode.
    """
    from compliance_os.web.models.tables_v2 import CheckRow

    check = (
        db.query(CheckRow)
        .filter(CheckRow.user_id == user_id, CheckRow.status == "saved")
        .first()
    )
    if check is None:
        check = CheckRow(track="stem_opt", status="saved", user_id=user_id, answers={})
        db.add(check)
        db.flush()
    return check


def _local_ocr_text(path) -> str:
    """Extract document text locally (no API). PDF→PyMuPDF, DOCX→python-docx,
    everything else→plain read. Returns "" on failure."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from compliance_os.web.services.extractor import extract_pdf_text_with_provenance

        return extract_pdf_text_with_provenance(str(path)).text or ""
    if suffix in {".docx", ".doc"}:
        from compliance_os.web.services.docx_reader import extract_text

        return extract_text(str(path)) or ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def local_upload_document(file_path: str, doc_type: str = "") -> dict:
    """Store a document into the local data room WITHOUT extracting facts.

    Deterministic + in-process: classify (if needed), copy the file under
    ~/.guardian/uploads/<check_id>/, create the DocumentRow, run versioning
    (register_uploaded_document), and read the text locally. Returns the
    doc_id, the parsed text, and the extraction schema so the caller's
    Claude can read the field values and submit record_extracted_facts.
    No server LLM, no HTTP.
    """
    import mimetypes
    import uuid as _uuid
    from pathlib import Path

    from compliance_os.facts.extraction_map import schema_for_doc_type
    from compliance_os.web.models.tables_v2 import DocumentRow
    from compliance_os.web.services.classifier import classify_file
    from compliance_os.web.services.document_store import register_uploaded_document

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    content = path.read_bytes()
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if not doc_type:
        doc_type = classify_file(str(path), mime_type, allow_ocr=False).doc_type or "unknown"

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        check = _get_local_check(db, user_id)
        # Resolve the uploads root from env LIVE (not settings, which is a
        # frozen singleton) so it honors GUARDIAN_HOME/GUARDIAN_DATA_DIR the
        # same way database.py resolves the DB path.
        guardian_home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
        upload_root = Path(os.environ.get("GUARDIAN_DATA_DIR") or (guardian_home / "uploads"))
        upload_dir = upload_root / check.id
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest = upload_dir / f"{_uuid.uuid4()}_{path.name}"
        dest.write_bytes(content)

        doc = DocumentRow(
            check_id=check.id,
            doc_type=doc_type,
            filename=path.name,
            file_path=str(dest),
            file_size=len(content),
            mime_type=mime_type,
            provenance={"classification": {"doc_type": doc_type, "source": "local_upload"}},
        )
        db.add(doc)
        db.flush()
        register_uploaded_document(check, doc, content, source_path=None, db=db)
        db.commit()
        db.refresh(doc)

        text = _local_ocr_text(dest)
        doc.ocr_text = text
        db.commit()

        return {
            "doc_id": doc.id,
            "doc_type": doc.doc_type,
            "text": text[:50_000],
            "extraction_schema": schema_for_doc_type(doc.doc_type),
        }
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_extraction_rehome.py::test_local_upload_document_stores_and_returns_schema -v`
Expected: PASS.

- [ ] **Step 5: Wire the `upload_document` MCP tool to the local path**

In `compliance_os/mcp_server.py`, in `upload_document`, add an early branch at the top of the body (after the docstring, before the `path = Path(file_path)` / `_upload_single_file` logic). Extend the existing `from compliance_os.local_engine import (...)` block to include `local_upload_document`:

```python
    if is_local_mode():
        return json.dumps(local_upload_document(file_path, doc_type), default=str, indent=2)
```

- [ ] **Step 6: Test the tool routing + commit**

```python
def test_mcp_upload_document_uses_local_path(local_db):
    from compliance_os import mcp_server

    src = Path(os.environ["GUARDIAN_HOME"]) / "doc.txt"
    src.write_text("SEVIS ID: N0009999999\n")
    out = json.loads(mcp_server.upload_document(str(src), doc_type="i20"))
    assert out["doc_type"] == "i20" and "doc_id" in out
```

Run: `pytest tests/test_extraction_rehome.py -q`
Expected: PASS (5 tests).

```bash
git add compliance_os/local_engine.py compliance_os/mcp_server.py tests/test_extraction_rehome.py
git commit -m "feat(extract): local-only upload_document (store+index, no server LLM)"
```

---

## Task 3: `record_extracted_facts` (project Claude's reads into the SoT)

**Files:**
- Modify: `compliance_os/local_engine.py`
- Modify: `compliance_os/mcp_server.py` (new tool)
- Test: `tests/test_extraction_rehome.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extraction_rehome.py::test_record_extracted_facts_projects_to_sot -v`
Expected: FAIL — `AttributeError: ... has no attribute 'local_record_extracted_facts'`.

- [ ] **Step 3: Add `local_record_extracted_facts` to `local_engine.py`**

Append to `compliance_os/local_engine.py`:

```python
def local_record_extracted_facts(doc_id: str, facts: list) -> dict:
    """Project Claude-extracted fields into the SoT for a stored document.

    `facts` is a list of {"field_name": <raw extractor field>, "value": str,
    "confidence": float (optional, default 1.0), "raw_text": str (optional)}.
    Each is written as an ExtractedFieldRow and — when it maps to a canonical
    fact_key and clears the confidence bar — projected into user_facts with
    supersession + conflict detection, reusing the deterministic
    _upsert_extracted_field path (no LLM). Returns the recorded field names,
    the resulting active facts, and any detected conflicts.
    """
    from compliance_os.web.models.tables_v2 import DocumentRow
    from compliance_os.web.services.document_store import _upsert_extracted_field

    db = next(get_session())
    try:
        doc = db.get(DocumentRow, doc_id)
        if doc is None:
            return {"error": f"document not found: {doc_id}"}

        recorded: list[str] = []
        for f in facts:
            field_name = f.get("field_name") or f.get("source_field")
            if not field_name:
                continue
            value = f.get("value")
            _upsert_extracted_field(
                db,
                doc=doc,
                field_name=field_name,
                value=str(value) if value is not None else None,
                confidence=f.get("confidence", 1.0),
                raw_text=f.get("raw_text"),
            )
            recorded.append(field_name)
        db.commit()

        user_id = get_local_user_id(db)
        rows = get_active_facts(db, user_id=user_id)
        return {
            "recorded_fields": recorded,
            "facts": [serialize_fact(r) for r in rows],
            "conflicts": [serialize_fact(r) for r in rows if r.detected_conflicts],
        }
    finally:
        db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extraction_rehome.py::test_record_extracted_facts_projects_to_sot tests/test_extraction_rehome.py::test_record_extracted_facts_unknown_doc_returns_error -v`
Expected: PASS (both).

- [ ] **Step 5: Add the `record_extracted_facts` MCP tool**

In `compliance_os/mcp_server.py`, add (extend the `from compliance_os.local_engine import (...)` block with `local_record_extracted_facts`):

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="Record extracted facts",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
def record_extracted_facts(doc_id: str, facts: list) -> str:
    """Submit the field values you read from a document into the SoT.

    Call this after parse_document + get_extraction_schema: read each
    schema field's value out of the document text, then submit them here.
    The engine writes them with provenance to the stored document and
    projects mapped fields into the user-facts source-of-truth, detecting
    conflicts with existing facts. Local mode only.

    Args:
        doc_id: The id returned by upload_document.
        facts: List of {"field_name": str, "value": str,
            "confidence": number (optional), "raw_text": str (optional)}.
    """
    if not is_local_mode():
        return json.dumps(
            {"error": "record_extracted_facts is only available in local mode."}
        )
    return json.dumps(
        local_record_extracted_facts(doc_id, facts), default=str, indent=2
    )
```

- [ ] **Step 6: Test + commit**

```python
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
```

Run: `pytest tests/test_extraction_rehome.py -q`
Expected: PASS (8 tests).

```bash
git add compliance_os/local_engine.py compliance_os/mcp_server.py tests/test_extraction_rehome.py
git commit -m "feat(extract): record_extracted_facts — project Claude's reads into the SoT"
```

---

## Task 4: `guardian_ask` → local grounding bundle (no model)

**Files:**
- Modify: `compliance_os/local_engine.py`
- Modify: `compliance_os/mcp_server.py` (`guardian_ask` local branch)
- Test: `tests/test_extraction_rehome.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extraction_rehome.py::test_local_ask_grounding_returns_context_and_refs -v`
Expected: FAIL — `AttributeError: ... has no attribute 'local_ask_grounding'`.

- [ ] **Step 3: Add `local_ask_grounding` to `local_engine.py`**

Append to `compliance_os/local_engine.py`:

```python
def local_ask_grounding(question: str) -> dict:
    """Gather local grounding for a question — chunks + facts — with NO model.

    Returns the retrieved document context and references so the caller's
    Claude composes the answer itself. This replaces the server-side
    RAG+LLM `guardian_ask` in local mode: retrieval stays local, the
    answer moves to the user's Claude.
    """
    from compliance_os.web.routers.chat import _build_context

    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        context_text, references = _build_context(user_id, db, query=question)
        return {
            "question": question,
            "context": context_text,
            "references": references,
        }
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_extraction_rehome.py::test_local_ask_grounding_returns_context_and_refs -v`
Expected: PASS.

- [ ] **Step 5: Wire the `guardian_ask` MCP tool to the local path**

In `compliance_os/mcp_server.py`, in `guardian_ask`, add an early branch at the top of the body (after the docstring), and extend the `from compliance_os.local_engine import (...)` block with `local_ask_grounding`. Also update the docstring to note that in local mode it returns grounding for you to answer from:

```python
    if is_local_mode():
        return json.dumps(local_ask_grounding(question), default=str, indent=2)
```

- [ ] **Step 6: Test the tool routing + commit**

```python
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
```

Run: `pytest tests/test_extraction_rehome.py -q`
Expected: PASS (10 tests).

```bash
git add compliance_os/local_engine.py compliance_os/mcp_server.py tests/test_extraction_rehome.py
git commit -m "feat(extract): guardian_ask returns local grounding bundle (no model) in local mode"
```

---

## Task 5: End-to-end loop integration test

**Files:**
- Test: `tests/test_extraction_rehome.py`

- [ ] **Step 1: Write the integration test**

```python
def test_full_local_extraction_loop(local_db):
    """parse → schema → upload → record → facts: the whole local loop."""
    from compliance_os import local_engine, mcp_server

    src = Path(os.environ["GUARDIAN_HOME"]) / "full_i20.txt"
    src.write_text("SEVIS ID: N0004445555\nProgram start: 2025-08-20\n")

    # 1. schema tells us what to read
    schema = json.loads(mcp_server.get_extraction_schema("i20"))
    assert any(e["source_field"] == "sevis_number" for e in schema)

    # 2. upload stores the doc + returns text for the model to read
    up = local_engine.local_upload_document(str(src), doc_type="i20")
    assert "N0004445555" in up["text"]

    # 3. record the value the model "read"
    local_engine.local_record_extracted_facts(
        up["doc_id"], [{"field_name": "sevis_number", "value": "N0004445555"}]
    )

    # 4. it shows up in the SoT
    facts = {f["fact_key"]: f["value"] for f in local_engine.local_get_facts()["facts"]}
    assert "sevis_id" in facts
```

- [ ] **Step 2: Run the full module**

Run: `pytest tests/test_extraction_rehome.py -v`
Expected: PASS (11 tests).

- [ ] **Step 3: Run the broader suite for regressions**

Run: `pytest tests/ -q`
Expected: the only failures are the pre-existing 13 (`test_election_83b`, `marketplace`, `auth`, `cases_router`, `database`). Confirm zero failures in `test_mcp_server.py`, `test_local_engine.py`, or `test_extraction_rehome.py`:
`pytest tests/ -q 2>&1 | grep -E "FAILED tests/(test_mcp_server|test_local_engine|test_extraction_rehome)" ` → must be empty.

- [ ] **Step 4: Commit**

```bash
git add tests/test_extraction_rehome.py
git commit -m "test(extract): end-to-end local extraction loop integration test"
```

---

## Self-Review Notes

**Spec coverage (§ Extraction-Loop Redesign):**
- `get_extraction_schema(doc_type)` → Task 1 (`schema_for_doc_type` + tool).
- `upload_document` becomes local-only (store + register + local OCR, **no server LLM**) → Task 2.
- `record_extracted_facts(doc_id, facts)` reusing the deterministic projection (`_upsert_extracted_field` → supersession + conflict) → Task 3.
- Chat → local retrieval + Claude answers (`guardian_ask` becomes a no-model grounding bundler) → Task 4.
- `query_documents` already local (Plan-1 era) — no change needed.
- Scanned-image vision path: the spec's `_local_ocr_text` returns PyMuPDF text; the "no text layer → Claude reads the image" affordance is a thin follow-up (return a signal when `text` is empty) and is intentionally deferred — note it, don't silently drop it.

**Type consistency:** `schema_for_doc_type` returns `list[dict]` with keys `source_field, fact_key, label, shape` — consumed identically by the tool and `local_upload_document`. `local_record_extracted_facts` accepts `field_name` (the raw extractor field), matching `_upsert_extracted_field(field_name=...)` and `fact_key_for(doc_type, field_name)`. Adapter envelopes: upload → `{doc_id, doc_type, text, extraction_schema}`; record → `{recorded_fields, facts, conflicts}`; ask → `{question, context, references}`.

**Scope (Plan 2 of 4):** no license/entitlement code (Plan 3), no Gmail/packaging (Plan 4). The local-mode branches reuse Plan-1 plumbing (`is_local_mode`, `get_local_user_id`, `get_session`, `serialize_fact`, `get_active_facts`).

**Known risks to watch during implementation:**
- `local_ask_grounding` imports `_build_context` from `compliance_os/web/routers/chat.py`; importing the router module executes its top level (FastAPI router construction). If that pulls a heavy/unsafe import at module load, move `_build_context` into a service module (`chat_context.py`) and import from there instead — report as DONE_WITH_CONCERNS if you do.
- `register_uploaded_document` and `_upsert_extracted_field` assume the document's check resolves to a user (`_resolve_user_id_for_document` via `check.user_id`); the singleton local check satisfies this. If a test shows facts not projecting, verify the check's `user_id` matches the local user.
- The async `_run` helper in Task 4's test mirrors the loop-safe pattern from `tests/test_local_engine.py` (avoids `asyncio.run()` contaminating `test_mcp_server.py`). Keep it.
