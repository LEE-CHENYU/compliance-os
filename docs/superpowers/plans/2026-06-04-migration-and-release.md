# Migration + Installer + Release Implementation Plan (Plan 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the local-first rollout: (1) let existing cloud users move their data room + facts SoT to the local extension via a hosted export + `guardian-mcp import`; (2) make the CLI installer configure **local mode** (consistent with the v2 `.dxt`); (3) bump the package to 2.0.0 and document the PyPI release the `.dxt` depends on.

**Architecture:** A shared `compliance_os/migration.py` owns serialization both directions — `export_user_data(db, user_id) -> bytes` (a zip of `data.json` + the on-disk upload files) and `import_data(zip_path) -> dict` (loads into the local `~/.guardian/guardian.db`). Rows are (de)serialized **generically** via SQLAlchemy column introspection — only datetimes need special handling; JSON/scalar columns pass through. Migration keeps original row IDs (preserving every FK: `documents_v2.check_id`, `extracted_fields.document_id`, `user_facts.superseded_by_id`) and remaps **only `user_id`** to the local singleton; file paths are rebased to `~/.guardian/uploads/<check_id>/`. A `GET /api/dashboard/export` endpoint and a `guardian-mcp import` CLI branch are thin wrappers over the shared module.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, `zipfile`/`io`/`json` (stdlib), pytest. No new deps.

**Scope:** the actual `twine upload` to PyPI is a manual release action (credentials, outward-facing) — documented in the appendix, NOT executed by this plan. `subject_chains`/`subject_document_links` are intentionally excluded from v1 export (non-essential for a data-room move; `user_facts` already carry their own `is_active`/`superseded_by_id` chain) — noted, not silently dropped.

**Reference (read before starting):**
- `compliance_os/web/models/tables_v2.py` — `CheckRow` (id, track, stage, status, answers[JSON], user_id, created_at, updated_at), `DocumentRow` (…file_path, content_hash, ocr_text, provenance[JSON]…), `ExtractedFieldRow` (id, document_id, field_name, field_value, confidence, raw_text), `UserFactRow` (…user_id, superseded_by_id, detected_conflicts[JSON]…)
- `compliance_os/web/models/database.py` — `create_engine_and_tables(db_path=None)`, `get_engine`, `get_session`, cached globals `_engine`/`_SessionLocal`; local-mode branch resolves `~/.guardian/guardian.db`
- `compliance_os/local_engine.py` — `get_local_user_id(db)`, `is_local_mode()`
- `compliance_os/web/routers/dashboard.py` — `_get_user(authorization, db)` auth pattern; uploads under `UPLOAD_DIR/<check_id>`
- `compliance_os/mcp_install.py` — `_mcp_server_config(api_url, token)` (line 82), `_write_toml_config(path, api_url, token)` (line 111), `_prompt_token()` (line 154), `install()` (line 183), `main()` (line 318, flat argv dispatch)

---

## File Structure

- **Create** `compliance_os/migration.py` — `export_user_data`, `import_data`, and the generic `_row_to_dict` / `_kwargs_from_dict` helpers.
- **Modify** `compliance_os/web/routers/dashboard.py` — add `GET /api/dashboard/export`.
- **Modify** `compliance_os/mcp_install.py` — local-mode config writers + a `guardian-mcp import <zip>` argv branch.
- **Modify** `pyproject.toml` — version → `2.0.0`.
- **Create** `tests/test_migration.py` — serialization, export, import, round-trip.

---

## Task 1: Installer writes local mode

**Files:**
- Modify: `compliance_os/mcp_install.py`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migration.py
import io
import json
import os
import zipfile
from pathlib import Path

import pytest


def test_mcp_server_config_is_local_mode():
    from compliance_os.mcp_install import _mcp_server_config

    cfg = _mcp_server_config("gdn_oc_aa_bb")
    assert cfg["env"] == {"GUARDIAN_LICENSE_KEY": "gdn_oc_aa_bb", "GUARDIAN_MODE": "local"}
    assert cfg["args"] == ["-m", "compliance_os.mcp_server"]


def test_write_toml_config_writes_local_env(tmp_path):
    from compliance_os.mcp_install import _write_toml_config

    path = tmp_path / "config.toml"
    _write_toml_config(path, "gdn_oc_cc_dd")
    text = path.read_text()
    assert 'GUARDIAN_LICENSE_KEY = "gdn_oc_cc_dd"' in text
    assert 'GUARDIAN_MODE = "local"' in text
    assert "GUARDIAN_API_URL" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migration.py::test_mcp_server_config_is_local_mode -v`
Expected: FAIL — `_mcp_server_config` takes `(api_url, token)` and writes `GUARDIAN_API_URL`/`GUARDIAN_TOKEN`.

- [ ] **Step 3: Rewrite the config writers + prompt + install() for local mode**

In `compliance_os/mcp_install.py`:

Replace `_mcp_server_config`:
```python
def _mcp_server_config(license_key: str) -> dict:
    return {
        "command": _python_path(),
        "args": ["-m", "compliance_os.mcp_server"],
        "env": {
            "GUARDIAN_LICENSE_KEY": license_key,
            "GUARDIAN_MODE": "local",
        },
    }
```

In `_write_toml_config`, change the signature to `def _write_toml_config(path: Path, license_key: str) -> bool:` and replace the `toml_block` env lines:
```python
[mcp_servers.guardian.env]
GUARDIAN_LICENSE_KEY = "{license_key}"
GUARDIAN_MODE = "local"
'''
```
(Keep the rest of `_write_toml_config` — the section-stripping loop — unchanged; it already strips lines starting with `GUARDIAN`.)

Replace `_prompt_token` with `_prompt_license_key`:
```python
def _prompt_license_key() -> str:
    print()
    print("  Guardian activation")
    print("  -------------------")
    print()
    print("  Everything runs locally on your machine — your documents never leave.")
    print("  Get your license key: guardiancompliance.app/connect  (sign in → Generate).")
    print()
    return input("  Paste Guardian license key: ").strip()
```

In `install()`, replace the `# Get token` block and the two writer calls:
```python
    # Get license key (local-first: no server URL needed)
    if local:
        license_key = os.environ.get("GUARDIAN_LICENSE_KEY", "")
    else:
        license_key = _prompt_license_key()

    # Write configs
    print()
    server_config = _mcp_server_config(license_key)

    for app in selected:
        path = app["path"]
        try:
            if app["format"] == "json":
                _write_json_config(path, server_config)
            elif app["format"] == "toml":
                _write_toml_config(path, license_key)
            print(f"  [ok] {app['name']}  →  {path}")
        except Exception as exc:
            print(f"  [!!] {app['name']}  →  {exc}")
```
(`os` is already imported at the top of `mcp_install.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_migration.py::test_mcp_server_config_is_local_mode tests/test_migration.py::test_write_toml_config_writes_local_env -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/mcp_install.py tests/test_migration.py
git commit -m "feat(install): guardian-mcp install configures local mode (license key, GUARDIAN_MODE=local)"
```

---

## Task 2: `migration.py` — export

**Files:**
- Create: `compliance_os/migration.py`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Write the failing test**

```python
def _make_source_db(tmp_path):
    """A standalone 'hosted-style' DB with one user + check + doc(file) + facts."""
    import secrets
    from sqlalchemy.orm import sessionmaker
    from compliance_os.web.models.database import create_engine_and_tables
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.models.tables_v2 import (
        CheckRow, DocumentRow, ExtractedFieldRow, UserFactRow,
    )

    engine = create_engine_and_tables(db_path=str(tmp_path / "source.db"))
    db = sessionmaker(bind=engine)()

    user = UserRow(email=f"src{secrets.token_hex(3)}@x.com", password_hash="x", role="user")
    db.add(user); db.flush()
    check = CheckRow(track="stem_opt", status="saved", user_id=user.id, answers={})
    db.add(check); db.flush()

    # a real upload file on disk
    updir = tmp_path / "src_uploads" / check.id
    updir.mkdir(parents=True)
    fpath = updir / "i20.txt"
    fpath.write_text("SEVIS ID: N0001234567")

    doc = DocumentRow(
        check_id=check.id, doc_type="i20", filename="i20.txt",
        file_path=str(fpath), file_size=fpath.stat().st_size,
        mime_type="text/plain", ocr_text="SEVIS ID: N0001234567",
    )
    db.add(doc); db.flush()
    db.add(ExtractedFieldRow(document_id=doc.id, field_name="sevis_number",
                             field_value="N0001234567", confidence=0.95))
    db.add(UserFactRow(user_id=user.id, fact_key="sevis_id", label="SEVIS ID",
                       category="immigration", track="student",
                       value={"v": "N0001234567"}, source_type="document",
                       is_active=True))
    db.commit()
    return db, user.id


def test_export_user_data_produces_zip(tmp_path):
    from compliance_os import migration

    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id)
    db.close()

    zf = zipfile.ZipFile(io.BytesIO(blob))
    names = set(zf.namelist())
    assert "data.json" in names
    assert any(n.startswith("uploads/") and n.endswith("i20.txt") for n in names)

    data = json.loads(zf.read("data.json"))
    assert len(data["checks"]) == 1
    assert len(data["documents"]) == 1
    assert len(data["extracted_fields"]) == 1
    assert len(data["user_facts"]) == 1
    assert data["user_facts"][0]["fact_key"] == "sevis_id"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migration.py::test_export_user_data_produces_zip -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.migration'`.

- [ ] **Step 3: Create `compliance_os/migration.py` with export**

```python
"""Hosted→local data migration for Guardian.

export_user_data(db, user_id) zips a user's data room + facts SoT (the
deterministic tables plus the on-disk upload files). import_data(zip) loads
it into the local ~/.guardian/guardian.db, keeping original row IDs (so all
FKs survive) and remapping only user_id to the local singleton user. Both
sides share the generic row (de)serialization below.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime
from sqlalchemy.orm import Session

from compliance_os.web.models.tables_v2 import (
    CheckRow,
    DocumentRow,
    ExtractedFieldRow,
    UserFactRow,
)

EXPORT_VERSION = 1


def _row_to_dict(row) -> dict:
    """Serialize an ORM row to a JSON-safe dict (datetimes → ISO strings)."""
    out: dict = {}
    for col in row.__table__.columns:
        value = getattr(row, col.key)
        if isinstance(value, datetime):
            value = value.isoformat()
        out[col.key] = value
    return out


def _kwargs_from_dict(model, data: dict, overrides: dict | None = None) -> dict:
    """Build constructor kwargs for `model` from a serialized dict, parsing
    DateTime columns back from ISO strings and dropping unknown keys."""
    cols = {c.key: c for c in model.__table__.columns}
    kwargs: dict = {}
    for key, value in data.items():
        col = cols.get(key)
        if col is None:
            continue
        if isinstance(col.type, DateTime) and isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                value = None
        kwargs[key] = value
    if overrides:
        kwargs.update(overrides)
    return kwargs


def export_user_data(db: Session, user_id: str) -> bytes:
    """Return a zip (bytes) of the user's checks, documents, extracted fields,
    user_facts, and the on-disk upload files."""
    checks = db.query(CheckRow).filter(CheckRow.user_id == user_id).all()
    check_ids = [c.id for c in checks]
    documents = (
        db.query(DocumentRow).filter(DocumentRow.check_id.in_(check_ids)).all()
        if check_ids else []
    )
    doc_ids = [d.id for d in documents]
    fields = (
        db.query(ExtractedFieldRow)
        .filter(ExtractedFieldRow.document_id.in_(doc_ids)).all()
        if doc_ids else []
    )
    facts = db.query(UserFactRow).filter(UserFactRow.user_id == user_id).all()

    data = {
        "export_version": EXPORT_VERSION,
        "checks": [_row_to_dict(c) for c in checks],
        "documents": [_row_to_dict(d) for d in documents],
        "extracted_fields": [_row_to_dict(f) for f in fields],
        "user_facts": [_row_to_dict(f) for f in facts],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json.dumps(data, indent=2, default=str))
        for d in documents:
            src = Path(d.file_path) if d.file_path else None
            if src and src.exists():
                # canonical relative path the importer rebases from
                zf.write(src, f"uploads/{d.check_id}/{src.name}")
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migration.py::test_export_user_data_produces_zip -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/migration.py tests/test_migration.py
git commit -m "feat(migration): export_user_data — zip a user's data room + facts SoT"
```

---

## Task 3: `migration.py` — import

**Files:**
- Modify: `compliance_os/migration.py`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield tmp_path
    database._engine = None
    database._SessionLocal = None


def test_import_lands_data_under_local_user(local_env, tmp_path):
    from compliance_os import migration
    from compliance_os.web.models import database
    from compliance_os.web.models.tables_v2 import DocumentRow, UserFactRow
    from compliance_os import local_engine

    # Build an export from a standalone source DB.
    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id)
    db.close()
    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(blob)

    summary = migration.import_data(str(zip_path))
    assert summary["checks"] == 1 and summary["documents"] == 1 and summary["user_facts"] == 1

    ldb = next(database.get_session())
    try:
        local_uid = local_engine.get_local_user_id(ldb)
        facts = ldb.query(UserFactRow).filter(UserFactRow.user_id == local_uid).all()
        assert any(f.fact_key == "sevis_id" for f in facts)
        doc = ldb.query(DocumentRow).first()
        # file rebased under the local home and actually copied
        assert str(tmp_path / "home") in doc.file_path
        assert Path(doc.file_path).exists()
        assert Path(doc.file_path).read_text() == "SEVIS ID: N0001234567"
    finally:
        ldb.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migration.py::test_import_lands_data_under_local_user -v`
Expected: FAIL — `AttributeError: module 'compliance_os.migration' has no attribute 'import_data'`.

- [ ] **Step 3: Add `import_data` to `migration.py`**

Append to `compliance_os/migration.py`:

```python
def _uploads_root() -> Path:
    import os

    home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
    return Path(os.environ.get("GUARDIAN_DATA_DIR") or (home / "uploads"))


def import_data(zip_path: str) -> dict:
    """Load an export zip into the local ~/.guardian/guardian.db.

    Keeps original row IDs (preserving FKs) and remaps user_id to the local
    singleton user. Rebases each document's file_path under the local uploads
    root and copies the bundled file. Skips rows whose id already exists, so
    re-import is safe. Returns a count summary.
    """
    import os

    os.environ["GUARDIAN_MODE"] = "local"
    from compliance_os.web.models import database

    database._engine = None
    database._SessionLocal = None

    from compliance_os.local_engine import get_local_user_id

    counts = {"checks": 0, "documents": 0, "extracted_fields": 0, "user_facts": 0}
    uploads_root = _uploads_root()

    with zipfile.ZipFile(zip_path) as zf:
        data = json.loads(zf.read("data.json"))

        db = next(database.get_session())
        try:
            local_uid = get_local_user_id(db)

            for c in data.get("checks", []):
                if db.get(CheckRow, c["id"]) is not None:
                    continue
                db.add(CheckRow(**_kwargs_from_dict(CheckRow, c, {"user_id": local_uid})))
                counts["checks"] += 1

            for d in data.get("documents", []):
                if db.get(DocumentRow, d["id"]) is not None:
                    continue
                src_name = Path(d["file_path"]).name if d.get("file_path") else None
                new_path = d.get("file_path")
                if src_name:
                    dest_dir = uploads_root / d["check_id"]
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / src_name
                    arc = f"uploads/{d['check_id']}/{src_name}"
                    try:
                        dest.write_bytes(zf.read(arc))
                    except KeyError:
                        pass  # file missing from the export — keep the row, rebased path
                    new_path = str(dest)
                db.add(DocumentRow(**_kwargs_from_dict(DocumentRow, d, {"file_path": new_path})))
                counts["documents"] += 1

            for f in data.get("extracted_fields", []):
                if db.get(ExtractedFieldRow, f["id"]) is not None:
                    continue
                db.add(ExtractedFieldRow(**_kwargs_from_dict(ExtractedFieldRow, f)))
                counts["extracted_fields"] += 1

            for f in data.get("user_facts", []):
                if db.get(UserFactRow, f["id"]) is not None:
                    continue
                db.add(UserFactRow(**_kwargs_from_dict(UserFactRow, f, {"user_id": local_uid})))
                counts["user_facts"] += 1

            db.commit()
        finally:
            db.close()

    return counts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migration.py::test_import_lands_data_under_local_user -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/migration.py tests/test_migration.py
git commit -m "feat(migration): import_data — load an export into local DB, remap user_id, rebase files"
```

---

## Task 4: Wire the export endpoint + the `guardian-mcp import` CLI

**Files:**
- Modify: `compliance_os/web/routers/dashboard.py`
- Modify: `compliance_os/mcp_install.py`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Write the failing test**

```python
def test_export_endpoint_streams_zip(tmp_path):
    from fastapi import Header
    from compliance_os.web.routers import dashboard

    db, user_id = _make_source_db(tmp_path)
    try:
        # call the endpoint function directly with a stubbed user
        from compliance_os.web.models.auth import UserRow
        user = db.query(UserRow).filter(UserRow.id == user_id).first()
        resp = dashboard.export_data(_user=user, db=db)
        body = b"".join(resp.body_iterator) if hasattr(resp, "body_iterator") else resp.body
        zf = zipfile.ZipFile(io.BytesIO(body))
        assert "data.json" in zf.namelist()
    finally:
        db.close()


def test_cli_import_subcommand(local_env, tmp_path, monkeypatch):
    from compliance_os import migration, mcp_install

    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id); db.close()
    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(blob)

    called = {}
    monkeypatch.setattr(migration, "import_data", lambda p: called.setdefault("path", p) or {"checks": 1})
    monkeypatch.setattr("sys.argv", ["guardian-mcp", "import", str(zip_path)])
    mcp_install.main()
    assert called["path"] == str(zip_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_migration.py::test_export_endpoint_streams_zip -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'export_data'`.

- [ ] **Step 3: Add the export endpoint**

In `compliance_os/web/routers/dashboard.py`, add (the `_get_user` helper, `StreamingResponse`, and `io` may need importing — add `from fastapi.responses import StreamingResponse` and `import io` if absent):

```python
@router.get("/export")
def export_data(
    _user=Depends(_get_user),
    db: Session = Depends(get_session),
):
    """Download the caller's data room + facts SoT as a zip, for migrating
    to the local extension (guardian-mcp import)."""
    from compliance_os.migration import export_user_data

    blob = export_user_data(db, _user.id)
    return StreamingResponse(
        io.BytesIO(blob),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="guardian_export.zip"'},
    )
```

(Note: the existing `_get_user` is a plain function, not a dependency. Either wrap it: `def _require_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow: return _get_user(authorization, db)` and `Depends(_require_user)`, OR keep the explicit `authorization` param pattern used by the other endpoints. Match whichever the file already uses — the test calls `export_data(_user=user, db=db)` directly, so the signature must accept a resolved user; adjust the test's kwargs to match the final signature.)

- [ ] **Step 4: Add the `import` argv branch to `mcp_install.main()`**

In `compliance_os/mcp_install.py`, at the top of `main()` (after `args = sys.argv[1:]`), add:

```python
    if args and args[0] == "import":
        if len(args) < 2:
            print("Usage: guardian-mcp import <export.zip>")
            return
        from compliance_os.migration import import_data

        summary = import_data(args[1])
        print(
            f"  Imported: {summary['checks']} checks, {summary['documents']} documents, "
            f"{summary['user_facts']} facts → ~/.guardian"
        )
        return
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_migration.py::test_export_endpoint_streams_zip tests/test_migration.py::test_cli_import_subcommand -v`
Expected: PASS (both). If the endpoint signature differs from the test's call, reconcile the test to the final signature (keep auth correct).

- [ ] **Step 6: Commit**

```bash
git add compliance_os/web/routers/dashboard.py compliance_os/mcp_install.py tests/test_migration.py
git commit -m "feat(migration): GET /api/dashboard/export + guardian-mcp import CLI"
```

---

## Task 5: Version bump + full round-trip + regression

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Bump the package version**

In `pyproject.toml`, change `version = "1.0.6"` to:
```toml
version = "2.0.0"
```

- [ ] **Step 2: Write the round-trip + version test**

```python
def test_full_export_import_roundtrip(local_env, tmp_path):
    from compliance_os import migration, local_engine
    from compliance_os.web.models import database
    from compliance_os.web.models.tables_v2 import UserFactRow

    db, user_id = _make_source_db(tmp_path)
    blob = migration.export_user_data(db, user_id); db.close()
    zp = tmp_path / "rt.zip"; zp.write_bytes(blob)

    first = migration.import_data(str(zp))
    second = migration.import_data(str(zp))  # idempotent: skip-existing
    assert first["user_facts"] == 1
    assert second["user_facts"] == 0  # nothing re-inserted

    ldb = next(database.get_session())
    try:
        uid = local_engine.get_local_user_id(ldb)
        assert ldb.query(UserFactRow).filter(UserFactRow.user_id == uid).count() == 1
    finally:
        ldb.close()


def test_package_version_is_2():
    import tomllib  # py311 stdlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    meta = tomllib.loads((root / "pyproject.toml").read_text())
    assert meta["project"]["version"] == "2.0.0"
```

- [ ] **Step 3: Run the full module**

Run: `pytest tests/test_migration.py -v`
Expected: PASS (all migration tests).

- [ ] **Step 4: Regression sweep**

Run: `pytest tests/ -q`
Expected: only the pre-existing 13 failures. Confirm zero failures in the touched/new modules:
`pytest tests/ -q 2>&1 | grep -E "FAILED tests/(test_migration|test_mcp_server|test_local_engine|test_extraction_rehome|test_license|test_gmail_gate_and_packaging)"` → must be empty.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/test_migration.py
git commit -m "build: bump compliance-os to 2.0.0; full export→import round-trip test"
```

---

## Release Appendix (manual — NOT executed by this plan)

After the PR stack (#3–#6 + this) merges to `main`, publish so the v2 `.dxt` can resolve its dependency:

```bash
# from a clean checkout of main, in the compliance-os conda env
python -m build                      # builds sdist + wheel into dist/
python -m twine upload dist/compliance_os-2.0.0*   # needs PyPI credentials
```

Then verify the `.dxt` resolves: install `frontend/public/guardian.dxt` into Claude Desktop, paste a license key, and confirm a tool runs (e.g. `get_extraction_schema i20`). This is a release action requiring PyPI credentials and is left to the maintainer.

---

## Self-Review Notes

**Spec/scope coverage:**
- Hosted→local migration → Tasks 2–4 (`migration.py` + endpoint + CLI), round-trip in Task 5.
- Installer local-mode (was the documented Plan-4 gap) → Task 1.
- `compliance-os==2.0.0` for the `.dxt` dependency → Task 5 (version) + the release appendix (publish).
- **Deferred intentionally:** `subject_chains`/links not exported (non-essential; noted); the actual PyPI `twine upload` is a credentialed manual step (appendix), not a test.

**Type consistency:** `export_user_data(db, user_id) -> bytes`; `import_data(zip_path) -> dict` (counts `{checks, documents, extracted_fields, user_facts}`); `_row_to_dict(row) -> dict`; `_kwargs_from_dict(model, data, overrides=None) -> dict`. The zip layout (`data.json` + `uploads/<check_id>/<name>`) is written by export and read by import identically. Migration keeps row IDs and remaps only `user_id`.

**Known risks to watch during implementation:**
- The `export_data` endpoint's auth signature: `_get_user` in `dashboard.py` is a plain helper, not a FastAPI dependency. The implementer must wire auth the way the rest of `dashboard.py` does (resolve the user from `authorization: str = Header(None)`), and make the Task-4 test call match the final signature. If unclear, prefer the explicit `authorization` Header param + `user = _get_user(authorization, db)` inside the body, and have the test pass a Bearer header for a created token.
- `import_data` mutates `os.environ["GUARDIAN_MODE"]` and resets the cached DB engine — correct for a CLI process, but in tests the `local_env` fixture already sets local mode and resets the globals; ensure the import re-reset doesn't point at a different path (the fixture sets `GUARDIAN_HOME`, which `import_data`'s reset honors via `configured_database_url`).
- Keep-IDs + skip-existing means re-import is additive-only (no merge/update). That's intended for v1 (migrate once into a fresh local install); document it if the behavior ever needs to become an upsert.
- `_row_to_dict` relies on JSON columns (`answers`, `provenance`, `source_ref`, `detected_conflicts`) being JSON-native — they are. No binary columns exist in the exported tables.
