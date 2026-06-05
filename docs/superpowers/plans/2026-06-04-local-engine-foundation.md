# Local Engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `GUARDIAN_MODE=local`, the Guardian MCP extension's facts source-of-truth and data path run fully in-process against `~/.guardian/guardian.db` with no HTTP to the hosted API — proven by a parity test showing the local path returns the same JSON shapes as the hosted `/api/facts` endpoints.

**Architecture:** Reuse the already transport-agnostic service layer in `compliance_os/web/services/user_facts.py` (`upsert_fact`, `get_active_facts`, `resolve_conflict`). Add a `GUARDIAN_MODE` switch, point the SQLAlchemy engine at a local SQLite DB at `~/.guardian/guardian.db` in local mode, create a singleton local user to scope SoT rows (no auth in single-user local mode), and add in-process adapters that the MCP facts tools call instead of `_api_get`/`_api_post`. Force local embeddings. This is Plan 1 of 4; it is the foundation the extraction re-home (Plan 2), license control plane (Plan 3), and Gmail/packaging (Plan 4) build on.

**Tech Stack:** Python 3.11, SQLAlchemy (SQLite), FastMCP (`mcp`), pytest. No new dependencies.

**Reference (read before starting):**
- `docs/superpowers/specs/2026-06-04-local-first-compliance-loop-design.md` — the design this implements
- `compliance_os/web/services/user_facts.py` — the service functions reused
- `compliance_os/web/routers/user_facts.py` — the HTTP shapes the local path must match (`_serialize`, response dicts)
- `compliance_os/web/models/database.py` — `configured_database_url`, `get_engine`, `get_session` (cached globals `_engine`, `_SessionLocal`)
- `compliance_os/mcp_server.py` — the tools `get_user_facts` / `set_user_fact` / `resolve_fact_conflict` (currently call `_api_get`/`_api_post`)

---

## File Structure

- **Create** `compliance_os/local_engine.py` — local-mode detection (`is_local_mode`), singleton local user (`get_local_user_id`), and in-process facts adapters (`local_get_facts`, `local_set_fact`, `local_resolve_conflict`, `force_local_embeddings`). Single responsibility: the in-process bridge between MCP tools and the service layer.
- **Modify** `compliance_os/web/models/database.py` — add a local-mode branch to `configured_database_url` so the engine uses `~/.guardian/guardian.db`.
- **Modify** `compliance_os/web/services/user_facts.py` — extract a shared `serialize_fact(row)` (moved from the router's `_serialize`) so the HTTP path and the local adapter serialize identically (DRY).
- **Modify** `compliance_os/web/routers/user_facts.py` — delegate `_serialize` to the new `serialize_fact`.
- **Modify** `compliance_os/mcp_server.py` — route the three facts tools to the local adapters when `is_local_mode()`; force local embeddings at startup in local mode.
- **Create** `tests/test_local_engine.py` — unit + parity tests.

---

## Task 1: Local-mode DB path resolution

**Files:**
- Modify: `compliance_os/web/models/database.py:16` (inside `configured_database_url`)
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_local_mode_db_url_points_at_guardian_home -v`
Expected: FAIL — `configured_database_url()` returns the `copilot.db` fallback, not `guardian.db`.

- [ ] **Step 3: Add the local-mode branch**

In `compliance_os/web/models/database.py`, inside `configured_database_url`, immediately after the `if db_path is not None:` block and before the `database_url = (os.environ.get("DATABASE_URL") ...)` line, insert:

```python
    if (os.environ.get("GUARDIAN_MODE") or "").strip().lower() == "local":
        guardian_home = Path(
            os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian")
        )
        guardian_home.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{guardian_home / 'guardian.db'}"
```

(`Path` and `os` are already imported at the top of `database.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_local_mode_db_url_points_at_guardian_home tests/test_local_engine.py::test_hosted_mode_db_url_unchanged -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/web/models/database.py tests/test_local_engine.py
git commit -m "feat(local): resolve SoT DB to ~/.guardian/guardian.db in local mode"
```

---

## Task 2: `is_local_mode()` + singleton local user

**Files:**
- Create: `compliance_os/local_engine.py`
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

Add a shared fixture and tests to `tests/test_local_engine.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_is_local_mode_reads_env -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.local_engine'`.

- [ ] **Step 3: Create the module with detection + local user**

```python
# compliance_os/local_engine.py
"""In-process local engine for the Guardian MCP extension.

When GUARDIAN_MODE=local, the MCP tools call these adapters instead of
proxying to the hosted Guardian API. Everything runs against the local
SQLite SoT at ~/.guardian/guardian.db using the already transport-
agnostic service layer in compliance_os.web.services.*.
"""
from __future__ import annotations

import os
import secrets

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session

LOCAL_USER_EMAIL = "local@guardian.local"


def is_local_mode() -> bool:
    """True when the extension should run fully in-process (no hosted API)."""
    return (os.environ.get("GUARDIAN_MODE") or "").strip().lower() == "local"


def get_local_user_id(db) -> str:
    """Return the singleton local user's id, creating it on first use.

    Local mode is single-user (whoever installed the extension), so there
    is no auth — we only need a stable user_id to scope SoT rows. The
    password_hash is random and never used for login.
    """
    user = (
        db.query(UserRow)
        .filter(UserRow.email == LOCAL_USER_EMAIL)
        .one_or_none()
    )
    if user is None:
        user = UserRow(
            email=LOCAL_USER_EMAIL,
            password_hash=secrets.token_hex(16),
            role="user",
        )
        db.add(user)
        db.commit()
    return user.id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_is_local_mode_reads_env tests/test_local_engine.py::test_get_local_user_id_is_stable_and_singleton -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/local_engine.py tests/test_local_engine.py
git commit -m "feat(local): add is_local_mode + singleton local user"
```

---

## Task 3: Shared `serialize_fact` (DRY the fact serializer)

**Files:**
- Modify: `compliance_os/web/services/user_facts.py` (add `serialize_fact`)
- Modify: `compliance_os/web/routers/user_facts.py:40` (delegate `_serialize`)
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_serialize_fact_matches_router_contract -v`
Expected: FAIL — `ImportError: cannot import name 'serialize_fact'`.

- [ ] **Step 3: Add `serialize_fact` to the service, delegate from the router**

In `compliance_os/web/services/user_facts.py`, add this function (place it near the top of the public functions, after the imports):

```python
def serialize_fact(row) -> dict:
    """Canonical JSON shape for a UserFactRow — shared by the HTTP router
    and the in-process local adapter so both surfaces emit identical output."""
    return {
        "id": row.id,
        "fact_key": row.fact_key,
        "label": row.label,
        "category": row.category,
        "track": row.track,
        "value": row.value,
        "notes": row.notes,
        "source_type": row.source_type,
        "source_ref": row.source_ref,
        "locked_at": row.locked_at.isoformat() if row.locked_at else None,
        "is_active": row.is_active,
        "superseded_by_id": row.superseded_by_id,
        "detected_conflicts": row.detected_conflicts or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
```

In `compliance_os/web/routers/user_facts.py`, replace the body of `_serialize` (currently defined around line 40) so it delegates:

```python
from compliance_os.web.services.user_facts import (
    get_active_facts,
    get_fact_history,
    resolve_conflict,
    serialize_fact,
    upsert_fact,
)


def _serialize(row) -> dict:
    return serialize_fact(row)
```

(Add `serialize_fact` to the existing import block; replace the old inline `_serialize` body.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_serialize_fact_matches_router_contract -v`
Expected: PASS.

Also run the existing facts router tests to confirm no regression:
Run: `pytest tests/ -k "fact" -v`
Expected: PASS (no behavior change — serialization is byte-identical).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/web/services/user_facts.py compliance_os/web/routers/user_facts.py tests/test_local_engine.py
git commit -m "refactor(facts): share serialize_fact between router and local engine"
```

---

## Task 4: In-process facts adapters

**Files:**
- Modify: `compliance_os/local_engine.py`
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_local_set_then_get_roundtrips -v`
Expected: FAIL — `AttributeError: module 'compliance_os.local_engine' has no attribute 'local_set_fact'`.

- [ ] **Step 3: Add the adapters to `local_engine.py`**

Append to `compliance_os/local_engine.py` (and extend the import at the top):

```python
from compliance_os.web.services.user_facts import (
    get_active_facts,
    resolve_conflict,
    serialize_fact,
    upsert_fact,
)


def local_get_facts(category: str = "", track: str = "") -> dict:
    """In-process equivalent of GET /api/facts → {"facts": [...]}."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        rows = get_active_facts(
            db, user_id=user_id,
            category=category or None, track=track or None,
        )
        return {"facts": [serialize_fact(r) for r in rows]}
    finally:
        db.close()


def local_set_fact(
    fact_key: str, value, notes: str = "", label: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts (a user-locked decision)."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        new_row, superseded = upsert_fact(
            db, user_id=user_id, fact_key=fact_key, value=value,
            source_type="decision_lock",
            source_ref={"ui_path": "mcp:set_user_fact"},
            notes=notes or None, label=label or None,
        )
        db.commit()
        return {
            "fact": serialize_fact(new_row),
            "superseded": serialize_fact(superseded) if superseded else None,
        }
    finally:
        db.close()


def local_resolve_conflict(
    fact_id: str, choice: str, user_value: str = "",
) -> dict:
    """In-process equivalent of POST /api/facts/{fact_id}/resolve."""
    db = next(get_session())
    try:
        user_id = get_local_user_id(db)
        row = resolve_conflict(
            db, user_id=user_id, fact_id=fact_id,
            choice=choice, user_value=user_value or None,
        )
        db.commit()
        return {"fact": serialize_fact(row)}
    finally:
        db.close()
```

(Remove the now-redundant standalone `from compliance_os.web.models.database import get_session` if duplicated — keep a single import block at the top.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_local_set_then_get_roundtrips tests/test_local_engine.py::test_local_set_fact_supersedes_previous -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/local_engine.py tests/test_local_engine.py
git commit -m "feat(local): in-process facts adapters (get/set/resolve)"
```

---

## Task 5: Wire MCP facts tools to local adapters

**Files:**
- Modify: `compliance_os/mcp_server.py` (`get_user_facts` ~line 766, `set_user_fact` ~line 806, `resolve_fact_conflict` ~line 852)
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

```python
def test_mcp_get_user_facts_uses_local_path(local_db):
    from compliance_os import local_engine, mcp_server

    # Seed via the local adapter
    local_engine.local_set_fact("sevis_id", "N0001234567")

    # The MCP tool (async) must return the seeded fact without any HTTP
    result = asyncio.run(mcp_server.get_user_facts())
    import json
    payload = json.loads(result)
    keys = {f["fact_key"] for f in payload["facts"]}
    assert "sevis_id" in keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_mcp_get_user_facts_uses_local_path -v`
Expected: FAIL — the tool tries to reach the hosted API (`_api_get`) and errors / returns an error JSON instead of the seeded fact.

- [ ] **Step 3: Add local-mode branches to the three tools**

At the **top of each tool body**, before the existing `_api_*` logic, add an early return. Add the import near the other top-of-file imports in `mcp_server.py`:

```python
from compliance_os.local_engine import (
    is_local_mode,
    local_get_facts,
    local_resolve_conflict,
    local_set_fact,
)
```

In `get_user_facts` (first line of the body, after the docstring):

```python
    if is_local_mode():
        return json.dumps(local_get_facts(category, track), default=str, indent=2)
```

In `set_user_fact`:

```python
    if is_local_mode():
        return json.dumps(
            local_set_fact(fact_key, value, notes=notes, label=label),
            default=str, indent=2,
        )
```

In `resolve_fact_conflict`:

```python
    if is_local_mode():
        return json.dumps(
            local_resolve_conflict(fact_id, choice, user_value=user_value),
            default=str, indent=2,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_mcp_get_user_facts_uses_local_path -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/mcp_server.py tests/test_local_engine.py
git commit -m "feat(local): route MCP facts tools to in-process engine in local mode"
```

---

## Task 6: Force local embeddings in local mode

**Files:**
- Modify: `compliance_os/local_engine.py` (add `force_local_embeddings`)
- Modify: `compliance_os/mcp_server.py` (call it at startup when local)
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the failing test**

```python
def test_force_local_embeddings_sets_provider(monkeypatch):
    from compliance_os import local_engine
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-be-ignored")
    monkeypatch.delenv("GUARDIAN_EMBEDDING_PROVIDER", raising=False)

    local_engine.force_local_embeddings()
    assert os.environ["GUARDIAN_EMBEDDING_PROVIDER"] == "local"
```

(`os` is imported in the module header established in Task 1.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_local_engine.py::test_force_local_embeddings_sets_provider -v`
Expected: FAIL — `AttributeError: module 'compliance_os.local_engine' has no attribute 'force_local_embeddings'`.

- [ ] **Step 3: Add `force_local_embeddings` and call it at startup**

In `compliance_os/local_engine.py`:

```python
def force_local_embeddings() -> None:
    """Pin embeddings to the local provider so no OpenAI key is ever used
    in local mode (privacy + $0 cost). Idempotent."""
    os.environ["GUARDIAN_EMBEDDING_PROVIDER"] = "local"
```

In `compliance_os/mcp_server.py`, near the top-level startup (where `_prewarm_embedding_model_bg` is set up / the server is configured), add:

```python
if is_local_mode():
    force_local_embeddings()
```

Extend the existing `from compliance_os.local_engine import (...)` to include `force_local_embeddings`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_local_engine.py::test_force_local_embeddings_sets_provider -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/local_engine.py compliance_os/mcp_server.py tests/test_local_engine.py
git commit -m "feat(local): force local embeddings (no OpenAI key) in local mode"
```

---

## Task 7: End-to-end parity test

**Files:**
- Test: `tests/test_local_engine.py`

- [ ] **Step 1: Write the parity test**

```python
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
```

- [ ] **Step 2: Run the full module to verify everything passes**

Run: `pytest tests/test_local_engine.py -v`
Expected: PASS (all tasks' tests green).

- [ ] **Step 3: Run the broader suite to confirm no regressions**

Run: `pytest tests/ -q`
Expected: PASS (or only pre-existing unrelated failures — note any in the commit body).

- [ ] **Step 4: Commit**

```bash
git add tests/test_local_engine.py
git commit -m "test(local): end-to-end parity between local adapter and hosted shapes"
```

---

## Self-Review Notes

**Spec coverage (this plan covers the foundation portion of the spec):**
- "Shared service facade / one engine" → Tasks 3–4 reuse `services/user_facts.py` directly; no logic duplicated.
- "`GUARDIAN_MODE=local`" → Task 1 (DB) + Task 2 (`is_local_mode`).
- "On-device layout: `~/.guardian/guardian.db`" → Task 1.
- "Local SQLite SoT, no auth, single local user" → Task 2.
- "Facts tools run in-process" → Tasks 4–5.
- "Force local embeddings" → Task 6.
- **Deferred to later plans (correctly out of scope here):** `record_extracted_facts` / `get_extraction_schema` / local-only `upload_document` / chat-retrieval (Plan 2); license control plane (Plan 3); Gmail + packaging (Plan 4). `query_documents` already runs locally and needs no change in this plan.

**Type consistency:** `serialize_fact` defined once (Task 3) and used in Tasks 4 & 7 and the router. Adapter return envelopes (`{"facts": [...]}`, `{"fact":..., "superseded":...}`, `{"fact":...}`) match the router handlers verified in `routers/user_facts.py`. `source_type="decision_lock"` is a member of `SOURCE_TYPES`.

**Known follow-up:** the `local_db` fixture reloads `database` and resets `_engine`/`_SessionLocal`; if other test modules import `database` at collection time, run this module in isolation if cross-module engine caching causes interference (`pytest tests/test_local_engine.py`).
