"""The canonical on-disk data room: copy-mirror tree + file↔data manifest.

Pins the contract: files are COPIED (originals stay), the tree is
<root>/<category>/<doc_type>/<filename>, manifest.json + INDEX.md map every
file to its extracted fields and asserted facts, and the sync runs
automatically on upload / fact recording."""

import json
import os
from pathlib import Path

import pytest

from compliance_os import dataroom as DR


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATAROOM_DIR", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


# ── unit: taxonomy ─────────────────────────────────────────────────

def test_category_for_mapped_doc_type_majority_vote():
    assert DR.category_for_doc_type("i20") == "immigration"
    assert DR.category_for_doc_type("i797") == "immigration"


def test_category_override_and_fallback():
    assert DR.category_for_doc_type("w2") == "tax"
    assert DR.category_for_doc_type("degree_certificate") == "education"
    assert DR.category_for_doc_type("totally_unknown_thing") == "other"


def test_chains_for_doc_type():
    assert "stem_opt" in DR.chains_for_doc_type("i20")
    assert "h1b" in DR.chains_for_doc_type("i797")
    assert DR.chains_for_doc_type("no_such_doc") == []


def test_safe_filename_strips_paths():
    assert DR._safe_filename("../../etc/passwd") == "passwd"
    assert DR._safe_filename("") == "document"


def test_dataroom_root_respects_guardian_home(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("GUARDIAN_DATAROOM_DIR", raising=False)
    assert DR.dataroom_root() == (tmp_path / "data-room").resolve()


# ── integration: active sync through the real write path ──────────

def _upload(tmp_path, name, text, doc_type):
    from compliance_os import local_engine
    src = Path(os.environ["GUARDIAN_HOME"]) / name
    src.write_text(text)
    out = local_engine.local_upload_document(str(src), doc_type=doc_type)
    assert "doc_id" in out, out
    return src, out


def test_upload_actively_files_a_copy(local_db, tmp_path):
    src, out = _upload(tmp_path, "my i20.txt", "SEVIS ID: N0001112222\n", "i20")

    # upload return carries the sync summary (active build)
    assert out["data_room"] and out["data_room"]["total"] == 1

    root = DR.dataroom_root()
    target = root / "immigration" / "i20" / "my i20.txt"
    assert target.exists(), f"canonical copy missing: {target}"
    # COPY not move — the original AND the upload-store copy both still exist
    assert src.exists()
    assert Path(json.loads((root / "manifest.json").read_text())["files"][0]["stored_at"]).exists()


def test_manifest_maps_file_to_extracted_fields_and_facts(local_db, tmp_path):
    from compliance_os import local_engine
    _, out = _upload(tmp_path, "i20.txt", "SEVIS ID: N0009998888\n", "i20")
    local_engine.local_record_extracted_facts(
        out["doc_id"], [{"field_name": "sevis_number", "value": "N0009998888"}]
    )
    manifest = json.loads((DR.dataroom_root() / "manifest.json").read_text())
    entry = next(e for e in manifest["files"] if e["doc_id"] == out["doc_id"])
    assert entry["extracted_fields"].get("sevis_number") == "N0009998888"
    assert entry["facts"].get("sevis_id") == "N0009998888"  # projected fact, mapped back to the file
    assert "stem_opt" in entry["chains"]
    assert manifest["facts_snapshot"].get("sevis_id") == "N0009998888"
    # human-readable index exists and mentions the file
    index = (DR.dataroom_root() / "INDEX.md").read_text()
    assert "i20.txt" in index and "sevis" in index.lower()


def test_sync_is_idempotent(local_db, tmp_path):
    _upload(tmp_path, "a.txt", "EAD card valid", "ead")
    from compliance_os import local_engine
    first = local_engine.local_build_data_room()
    assert first["copied"] == 0 and first["unchanged"] == 1  # already filed by upload
    second = local_engine.local_build_data_room()
    assert second["copied"] == 0 and second["unchanged"] == 1


def test_same_filename_same_doc_type_supersedes_to_one_active_copy(local_db, tmp_path):
    # Versioning treats same filename + doc_type as a NEW VERSION of the same
    # document; the mirror reflects only the active version.
    _upload(tmp_path, "doc.txt", "SEVIS ID: N0000000001", "i20")
    src2 = Path(os.environ["GUARDIAN_HOME"]) / "sub"
    src2.mkdir()
    (src2 / "doc.txt").write_text("SEVIS ID: N0000000002")
    from compliance_os import local_engine
    local_engine.local_upload_document(str(src2 / "doc.txt"), doc_type="i20")
    manifest = json.loads((DR.dataroom_root() / "manifest.json").read_text())
    assert len(manifest["files"]) == 1
    assert manifest["files"][0]["version"] == 2
    # and the mirrored copy is the NEW content
    assert "N0000000002" in (DR.dataroom_root() / manifest["files"][0]["path"]).read_text()


def test_distinct_docs_sanitizing_to_same_name_are_disambiguated(local_db, tmp_path):
    # Two genuinely distinct active docs whose names collide in the tree get
    # a doc-id prefix instead of overwriting each other.
    from compliance_os import local_engine
    from compliance_os.dataroom import sync_data_room
    from compliance_os.web.models.tables_v2 import DocumentRow

    _upload(tmp_path, "x.txt", "SEVIS ID: N0000000001", "i20")
    db = next(local_db.get_session())
    try:
        user_id = local_engine.get_local_user_id(db)
        existing = db.query(DocumentRow).first()
        src = Path(os.environ["GUARDIAN_HOME"]) / "y.txt"
        src.write_text("different content entirely")
        db.add(DocumentRow(
            check_id=existing.check_id, doc_type="i20", filename="x.txt",
            file_path=str(src), file_size=src.stat().st_size, mime_type="text/plain",
        ))
        db.commit()
        summary = sync_data_room(db, user_id)
    finally:
        db.close()
    assert summary["total"] == 2
    manifest = json.loads((DR.dataroom_root() / "manifest.json").read_text())
    paths = [e["path"] for e in manifest["files"]]
    assert len(set(paths)) == 2  # disambiguated
    for p in paths:
        assert (DR.dataroom_root() / p).exists()


def test_record_wedge_mentions_data_room(local_db, tmp_path):
    from compliance_os import local_engine, presenters
    _, out = _upload(tmp_path, "b.txt", "SEVIS ID: N0005556666\n", "i20")
    res = local_engine.local_record_extracted_facts(
        out["doc_id"], [{"field_name": "sevis_number", "value": "N0005556666"}]
    )
    card = presenters.format_record_wedge(res)
    assert "Data room synced" in card


# ── presenter card ─────────────────────────────────────────────────

def test_format_data_room_card():
    from compliance_os import presenters
    card = presenters.format_data_room({
        "root": "/home/u/.guardian/data-room", "manifest": "...",
        "total": 3, "copied": 1, "updated": 0, "unchanged": 2,
        "categories": {"immigration": 2, "tax": 1},
    })
    assert "3 files" in card
    assert "immigration 2" in card and "tax 1" in card
    assert "copies" in card  # states copy-not-move


def test_format_data_room_empty():
    from compliance_os import presenters
    assert "Empty so far" in presenters.format_data_room({"total": 0})
