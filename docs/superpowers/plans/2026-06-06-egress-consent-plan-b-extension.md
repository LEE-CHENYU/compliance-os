# Egress Consent — Plan B: Extension SoT-Share Path + Consent Primitive + Server Endpoint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a consent-gated path to upload the local SoT + documents to Guardian cloud (`share_data_room`), backed by a per-purpose consent store, a server receiver endpoint, and a regression test locking `guardian_ask` to grounding-only — shipped as `compliance-os` 2.0.2.

**Architecture:** A Python consent store at `~/.guardian/consent.json` (always→disk, session→in-memory, once→nothing), keyed per `purpose`. A `share_data_room(purpose, confirm, remember)` MCP tool reuses `export_user_data` for the payload and POSTs it to a new `POST /api/context/share` server endpoint (authenticated by the license token), which stores it per-user for future services. Nothing egresses until `confirm=True`.

**Tech Stack:** Python 3.11, FastMCP, SQLAlchemy (SQLite), FastAPI, pytest.

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-05-egress-consent-design.md` (§2 contract, §4 Track 2, §4.5 server endpoint)
- `compliance_os/migration.py` — `export_user_data(db, user_id) -> bytes` (zip of checks/documents/extracted_fields/user_facts + upload files).
- `compliance_os/local_engine.py` — `is_local_mode()`, `get_local_user_id(db)`, `get_session` (imported from `web.models.database`); home convention `Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))` (see `licensing.py:53`, `local_engine.py:121`).
- `compliance_os/mcp_server.py` — `GatedMCP`/`@mcp.tool(annotations=ToolAnnotations(...))`, `is_local_mode()`, `_resolve_token()`, hosted multipart POST pattern (l.718–735), `guardian_ask` local branch returns `local_ask_grounding`.
- `compliance_os/web/models/tables_v2.py` — `Base`; add new tables here (init `create_all` auto-creates NEW tables — `database.py:61/75/106`).
- `compliance_os/web/routers/dashboard.py` — auth pattern `_get_user(authorization: str = Header(None), db = Depends(get_session))` → `get_bearer_payload`; `APIRouter(prefix="/api/dashboard")`; file-write pattern (l.512–514). Register routers in `compliance_os/web/app.py` (`app.include_router(...)`).

**Consent contract (spec §2):** `egress_type="share_data_room"`, keyed by `purpose` (a named service, e.g. `"lawyer-matching"`), `destination="guardian_cloud"`, `data_categories=["sot_facts","documents"]`. Decisions `once`/`session`/`always`/`deny`; "Always" persists per-purpose, revocable.

---

## Task 1: Consent store (`consent.py`)

**Files:**
- Create: `compliance_os/consent.py`
- Test: `tests/test_consent.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_consent.py`:
```python
import importlib


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    import compliance_os.consent as consent
    importlib.reload(consent)  # reset module-level session set + re-resolve home
    return consent


def test_no_consent_initially(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    assert consent.has_consent("lawyer-matching") is False


def test_once_does_not_persist(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "once", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("lawyer-matching") is False


def test_session_in_memory_only(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "session", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("lawyer-matching") is True
    assert not (tmp_path / "consent.json").exists()


def test_always_persists_and_survives_reload(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    consent2 = _fresh(monkeypatch, tmp_path)  # simulate process restart
    assert consent2.has_consent("lawyer-matching") is True


def test_revoke_clears_always(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    consent.revoke_consent("lawyer-matching")
    assert consent.has_consent("lawyer-matching") is False


def test_per_purpose_isolation(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("cpa-matching") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n compliance-os pytest tests/test_consent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.consent'`.

- [ ] **Step 3: Implement `consent.py`**

Create `compliance_os/consent.py`:
```python
"""Egress consent store for the local extension.

Per-purpose consent for sending the local SoT/documents off-device.
`always` persists to ~/.guardian/consent.json; `session` lives for the
process lifetime; `once` is not stored. Keyed by purpose.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_SESSION: set[str] = set()


def _home() -> Path:
    return Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))


def _store_path() -> Path:
    return _home() / "consent.json"


def _load() -> dict:
    p = _store_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (ValueError, OSError):
        return {}


def has_consent(purpose: str) -> bool:
    if purpose in _SESSION:
        return True
    return _load().get(purpose, {}).get("scope") == "always"


def record_consent(purpose: str, scope: str, *, destination: str, data_categories: list[str]) -> None:
    if scope == "always":
        store = _load()
        store[purpose] = {
            "egress_type": "share_data_room",
            "purpose": purpose,
            "destination": destination,
            "data_categories": data_categories,
            "scope": "always",
            "granted_at": datetime.now(timezone.utc).isoformat(),
        }
        home = _home()
        home.mkdir(parents=True, exist_ok=True)
        _store_path().write_text(json.dumps(store, indent=2))
    elif scope == "session":
        _SESSION.add(purpose)
    # "once" / "deny": nothing stored.


def revoke_consent(purpose: str) -> None:
    _SESSION.discard(purpose)
    store = _load()
    if purpose in store:
        del store[purpose]
        _store_path().write_text(json.dumps(store, indent=2))


def list_consents() -> list[dict]:
    """Persisted (always) grants plus active session grants."""
    out = list(_load().values())
    persisted = {r["purpose"] for r in out}
    for purpose in _SESSION:
        if purpose not in persisted:
            out.append({"purpose": purpose, "scope": "session", "egress_type": "share_data_room"})
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n compliance-os pytest tests/test_consent.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/consent.py tests/test_consent.py
git commit -m "feat(egress): per-purpose consent store"
```

---

## Task 2: `local_share_data_room` orchestration

**Files:**
- Modify: `compliance_os/local_engine.py`
- Test: `tests/test_share_data_room.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_share_data_room.py`:
```python
import importlib

import pytest


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    import compliance_os.consent as consent
    importlib.reload(consent)
    yield
    database._engine = None
    database._SessionLocal = None


def test_share_requires_consent_then_uploads(local_env, monkeypatch):
    from compliance_os import local_engine

    posted = {}
    def fake_post(zip_bytes, purpose, token):
        posted["bytes"] = zip_bytes
        posted["purpose"] = purpose
        return {"reference_id": "ref-123", "purpose": purpose}
    monkeypatch.setattr(local_engine, "_post_context_share", fake_post)

    # No prior consent, no confirm -> a consent request, nothing posted.
    res = local_engine.local_share_data_room("lawyer-matching", confirm=False, remember="once")
    assert res["status"] == "consent_required"
    assert "lawyer-matching" in res["purpose"]
    assert "bytes" not in posted

    # Confirm -> exactly one upload, reference returned.
    res2 = local_engine.local_share_data_room("lawyer-matching", confirm=True, remember="always")
    assert res2["status"] == "shared"
    assert res2["reference_id"] == "ref-123"
    assert posted["purpose"] == "lawyer-matching"
    assert isinstance(posted["bytes"], (bytes, bytearray)) and len(posted["bytes"]) > 0

    # Always grant recorded -> a later call proceeds without a request.
    posted.clear()
    res3 = local_engine.local_share_data_room("lawyer-matching", confirm=False, remember="once")
    assert res3["status"] == "shared"
    assert posted["purpose"] == "lawyer-matching"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n compliance-os pytest tests/test_share_data_room.py -v`
Expected: FAIL — `module 'compliance_os.local_engine' has no attribute 'local_share_data_room'`.

- [ ] **Step 3: Implement in `local_engine.py`** (append at end of file)

```python
GUARDIAN_CLOUD_URL = os.environ.get("GUARDIAN_CLOUD_URL", "https://guardian-compliance.fly.dev")

_SHARE_DATA_CATEGORIES = ["sot_facts", "documents"]


def _resolve_license_token() -> str:
    """The license key is the bearer token for cloud egress."""
    return os.environ.get("GUARDIAN_LICENSE_KEY", "")


def _post_context_share(zip_bytes: bytes, purpose: str, token: str) -> dict:
    """POST the export zip to the cloud context-share endpoint. Real network."""
    import json
    import uuid
    from urllib import request

    boundary = uuid.uuid4().hex
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\n{purpose}\r\n".encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"data_room.zip\"\r\nContent-Type: application/zip\r\n\r\n".encode()
    )
    parts.append(zip_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{GUARDIAN_CLOUD_URL}/api/context/share", data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def local_share_data_room(purpose: str, confirm: bool = False, remember: str = "once") -> dict:
    """Consent-gated upload of the local SoT + documents to Guardian cloud."""
    from compliance_os import consent
    from compliance_os.migration import export_user_data

    def _do_share() -> dict:
        db = next(get_session())
        try:
            user_id = get_local_user_id(db)
            zip_bytes = export_user_data(db, user_id)
        finally:
            db.close()
        result = _post_context_share(zip_bytes, purpose, _resolve_license_token())
        return {"status": "shared", "purpose": purpose,
                "reference_id": result.get("reference_id"),
                "message": f"Shared your data room for '{purpose}'."}

    if consent.has_consent(purpose):
        return _do_share()
    if not confirm:
        return {
            "status": "consent_required",
            "purpose": purpose,
            "destination": "Guardian cloud",
            "data_categories": _SHARE_DATA_CATEGORIES,
            "message": (
                f"This will upload your facts source-of-truth and your documents to "
                f"Guardian's cloud for '{purpose}'. Nothing is sent unless you approve. "
                f"To proceed, call again with confirm=true and remember set to "
                f"'once', 'session', or 'always'. To decline, do nothing."
            ),
        }
    consent.record_consent(purpose, remember, destination="guardian_cloud",
                           data_categories=_SHARE_DATA_CATEGORIES)
    return _do_share()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n compliance-os pytest tests/test_share_data_room.py -v`
Expected: PASS (1 test, 3 phases).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/local_engine.py tests/test_share_data_room.py
git commit -m "feat(egress): consent-gated local_share_data_room (reuses export_user_data)"
```

---

## Task 3: MCP tools — share + consent management

**Files:**
- Modify: `compliance_os/mcp_server.py`
- Test: `tests/test_mcp_share_tools.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_share_tools.py`:
```python
import importlib
import json

import pytest


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    import compliance_os.consent as consent
    importlib.reload(consent)
    yield
    database._engine = None
    database._SessionLocal = None


def test_share_tool_gates_then_management(local_env, monkeypatch):
    from compliance_os import local_engine, mcp_server

    monkeypatch.setattr(local_engine, "_post_context_share",
                        lambda b, p, t: {"reference_id": "ref-9", "purpose": p})

    out = json.loads(mcp_server.share_data_room("lawyer-matching"))
    assert out["status"] == "consent_required"

    out2 = json.loads(mcp_server.share_data_room("lawyer-matching", confirm=True, remember="always"))
    assert out2["status"] == "shared"

    listed = json.loads(mcp_server.list_egress_consents())
    assert any(c["purpose"] == "lawyer-matching" for c in listed["consents"])

    revoked = json.loads(mcp_server.revoke_egress_consent("lawyer-matching"))
    assert revoked["revoked"] == "lawyer-matching"
    listed2 = json.loads(mcp_server.list_egress_consents())
    assert all(c["purpose"] != "lawyer-matching" for c in listed2["consents"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n compliance-os pytest tests/test_mcp_share_tools.py -v`
Expected: FAIL — `module 'compliance_os.mcp_server' has no attribute 'share_data_room'`.

- [ ] **Step 3: Add the import** — extend the existing `from compliance_os.local_engine import (...)` block in `mcp_server.py` with `local_share_data_room`.

- [ ] **Step 4: Add the tools** (place near the other local-mode tools, e.g. after `cross_check_filings`)

```python
@mcp.tool(
    annotations=ToolAnnotations(
        title="Share data room (cloud)",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    ),
)
def share_data_room(purpose: str, confirm: bool = False, remember: str = "once") -> str:
    """Upload your local facts source-of-truth + documents to Guardian's cloud
    for a named purpose (e.g. a lawyer-matching service) — ONLY with your explicit
    approval. With no prior 'always' grant and confirm=false, this returns a consent
    request describing exactly what will be sent and where; show it to the user and,
    if they approve, call again with confirm=true and remember='once'|'session'|'always'.
    Nothing leaves the device until confirm=true (or a prior 'always' grant exists).

    Args:
        purpose: The service/purpose the data is shared for (e.g. "lawyer-matching").
        confirm: Set true only after the user has approved this upload.
        remember: How long to remember approval — "once", "session", or "always".
    """
    if not is_local_mode():
        return json.dumps({"error": "share_data_room is only available in local mode."})
    return json.dumps(local_share_data_room(purpose, confirm=confirm, remember=remember), default=str, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(title="List egress consents", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
)
def list_egress_consents() -> str:
    """List the purposes you've approved for sharing your data room to Guardian cloud."""
    if not is_local_mode():
        return json.dumps({"error": "list_egress_consents is only available in local mode."})
    from compliance_os import consent
    return json.dumps({"consents": consent.list_consents()}, default=str, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(title="Revoke egress consent", readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
def revoke_egress_consent(purpose: str) -> str:
    """Revoke a previously granted data-room sharing consent for a purpose.

    Args:
        purpose: The purpose to revoke (e.g. "lawyer-matching").
    """
    if not is_local_mode():
        return json.dumps({"error": "revoke_egress_consent is only available in local mode."})
    from compliance_os import consent
    consent.revoke_consent(purpose)
    return json.dumps({"revoked": purpose}, default=str, indent=2)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n compliance-os pytest tests/test_mcp_share_tools.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add compliance_os/mcp_server.py tests/test_mcp_share_tools.py
git commit -m "feat(egress): share_data_room + list/revoke consent MCP tools"
```

---

## Task 4: `guardian_ask` local regression test

**Files:**
- Test: `tests/test_guardian_ask_local.py`

- [ ] **Step 1: Write the test**

Create `tests/test_guardian_ask_local.py`:
```python
import asyncio


def test_guardian_ask_local_makes_no_external_llm_call(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    from compliance_os import mcp_server

    # Any hosted egress path must NOT be reached in local mode.
    async def _boom(*a, **k):
        raise AssertionError("guardian_ask hit the hosted /api/chat path in local mode")
    monkeypatch.setattr(mcp_server, "_api_post", _boom)

    out = asyncio.run(mcp_server.guardian_ask("Do I need to file FBAR?"))
    assert isinstance(out, str) and out  # returns local grounding, no external call
    database._engine = None
    database._SessionLocal = None
```

- [ ] **Step 2: Run test to verify it passes** (this locks in existing behavior — should pass immediately)

Run: `conda run -n compliance-os pytest tests/test_guardian_ask_local.py -v`
Expected: PASS. If it FAILS by reaching `_boom`, the local branch regressed — fix `guardian_ask` to return `local_ask_grounding(question)` in local mode before debugging the test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_guardian_ask_local.py
git commit -m "test(egress): lock guardian_ask local mode to grounding-only (no egress)"
```

---

## Task 5: professional-search transparency note

**Files:**
- Modify: `compliance_os/mcp_server.py` (the `lawyer_search_plan` tool, ~l.1870)
- Test: `tests/test_search_plan_note.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_search_plan_note.py`:
```python
import json


def test_lawyer_search_plan_includes_transparency_note(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import mcp_server

    out = mcp_server.lawyer_search_plan(vertical="immigration")
    data = json.loads(out)
    assert "privacy_note" in data
    assert "generic" in data["privacy_note"].lower()
    assert "personal facts are not included" in data["privacy_note"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n compliance-os pytest tests/test_search_plan_note.py -v`
Expected: FAIL — `KeyError: 'privacy_note'` (or assertion error).

- [ ] **Step 3: Add the note** — in `lawyer_search_plan`, where it builds `plan` before `return json.dumps(plan, indent=2)`, attach the note. Replace the success return with:

```python
        plan["privacy_note"] = (
            "Claude will search the web using generic persona queries; your "
            "personal facts are not included."
        )
        return json.dumps(plan, indent=2)
```
(If `plan` is a list rather than a dict, wrap it: `return json.dumps({"plan": plan, "privacy_note": "...same text..."}, indent=2)` — and update the test's access path to match. Inspect the actual `build_search_plan` return shape first and keep the test and code consistent.)

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n compliance-os pytest tests/test_search_plan_note.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add compliance_os/mcp_server.py tests/test_search_plan_note.py
git commit -m "feat(egress): transparency note on professional-search plan output"
```

---

## Task 6: Server endpoint `POST /api/context/share`

**Files:**
- Modify: `compliance_os/web/models/tables_v2.py` (add `SharedContextRow`)
- Create: `compliance_os/web/routers/context.py`
- Modify: `compliance_os/web/app.py` (register router)
- Test: `tests/test_context_share_endpoint.py`

- [ ] **Step 1: Add the table** — append to `tables_v2.py` (use the same `Base` the other rows use):

```python
class SharedContextRow(Base):
    __tablename__ = "shared_context"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    purpose = Column(String, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```
(Ensure `uuid`, `datetime`, `timezone`, and the SQLAlchemy `Column/String/DateTime` imports already present in `tables_v2.py` are used; if `uuid`/`datetime` aren't imported there, add `import uuid` and `from datetime import datetime, timezone` at the top.)

- [ ] **Step 2: Write the failing test**

Create `tests/test_context_share_endpoint.py`:
```python
import io
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    database.init_db()
    from compliance_os.web.app import app
    return TestClient(app)


def _make_user_and_token(monkeypatch):
    # Reuse the project's auth: create a user + a valid bearer token.
    from compliance_os.web.models.database import get_session
    from compliance_os.web.services.auth_service import create_token_for_user
    from compliance_os.web.models.auth import UserRow
    db = next(get_session())
    try:
        user = UserRow(email="t@example.com")
        db.add(user); db.commit()
        token = create_token_for_user(user)
        return user.id, token
    finally:
        db.close()


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", "{}")
    return buf.getvalue()


def test_share_requires_auth(client):
    r = client.post("/api/context/share", data={"purpose": "lawyer-matching"},
                    files={"file": ("d.zip", _zip_bytes(), "application/zip")})
    assert r.status_code == 401


def test_share_stores_blob_and_row(client, monkeypatch):
    uid, token = _make_user_and_token(monkeypatch)
    r = client.post(
        "/api/context/share",
        headers={"Authorization": f"Bearer {token}"},
        data={"purpose": "lawyer-matching"},
        files={"file": ("d.zip", _zip_bytes(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["purpose"] == "lawyer-matching" and body["reference_id"]

    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.tables_v2 import SharedContextRow
    db = next(get_session())
    try:
        row = db.query(SharedContextRow).filter(SharedContextRow.user_id == uid).first()
        assert row is not None and row.purpose == "lawyer-matching"
        from pathlib import Path
        assert Path(row.path).exists()
    finally:
        db.close()
```
(Before running, verify the real helper names: `create_token_for_user` and `UserRow(email=...)` — if the project names differ, use the actual token-mint + user-create helpers from `auth_service.py`/`models/auth.py`. Keep the test and endpoint consistent with what exists.)

- [ ] **Step 3: Run test to verify it fails**

Run: `conda run -n compliance-os pytest tests/test_context_share_endpoint.py -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 4: Implement the router**

Create `compliance_os/web/routers/context.py`:
```python
"""Receive a user's exported data room for a named purpose, for future services."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import DATA_DIR, get_session
from compliance_os.web.models.tables_v2 import SharedContextRow
from compliance_os.web.services.auth_service import get_bearer_payload

router = APIRouter(prefix="/api/context", tags=["context"])

SHARED_DIR = DATA_DIR / "shared_context"


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


@router.post("/share")
async def share_context(
    purpose: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_session),
):
    user = _get_user(authorization, db)
    content = await file.read()
    user_dir = SHARED_DIR / user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    ref = str(uuid.uuid4())
    dest = user_dir / f"{purpose}-{ref}.zip"
    dest.write_bytes(content)
    row = SharedContextRow(id=ref, user_id=user.id, purpose=purpose, path=str(dest))
    db.add(row)
    db.commit()
    return {"reference_id": ref, "purpose": purpose, "stored_at": str(dest)}
```

- [ ] **Step 5: Register the router** — in `compliance_os/web/app.py`, add next to the other `include_router` lines:

```python
from compliance_os.web.routers import context as context_router
app.include_router(context_router.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `conda run -n compliance-os pytest tests/test_context_share_endpoint.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add compliance_os/web/models/tables_v2.py compliance_os/web/routers/context.py compliance_os/web/app.py tests/test_context_share_endpoint.py
git commit -m "feat(egress): POST /api/context/share receiver + SharedContextRow"
```

---

## Task 7: Release 2.0.2

**Files:**
- Modify: `pyproject.toml`, `compliance_os/__init__.py`, `scripts/build_dxt.py`

- [ ] **Step 1: Bump versions**

In `pyproject.toml`: `version = "2.0.1"` → `version = "2.0.2"`.
In `compliance_os/__init__.py`: `__version__ = "2.0.1"` → `__version__ = "2.0.2"`.
In `scripts/build_dxt.py`: `COMPLIANCE_OS_VERSION = "==2.0.1"` → `"==2.0.2"`, and the manifest `"version": "2.0.1"` → `"2.0.2"`.

- [ ] **Step 2: Advertise the new tool in the dxt manifest** — in `scripts/build_dxt.py` `MANIFEST["tools"]`, after the `cross_check_filings` entry add:

```python
        {"name": "share_data_room",      "description": "Upload your data room to Guardian cloud (with your approval)"},
```

- [ ] **Step 3: Full regression sweep**

Run: `conda run -n compliance-os pytest tests/ -q 2>&1 | grep -E "FAILED tests/(test_consent|test_share_data_room|test_mcp_share_tools|test_guardian_ask_local|test_search_plan_note|test_context_share_endpoint|test_mcp_server|test_local_engine)"`
Expected: empty (no failures in the new or local-first modules). The only acceptable failures in the full suite are the pre-existing ones (`test_auth`, `test_cases_router`, `test_database`, `test_election_83b_service`, `test_marketplace_slice3`).

- [ ] **Step 4: Build the wheel + verify packaged data**

Run:
```bash
cd /Users/lichenyu/compliance-os && rm -rf dist build compliance_os.egg-info && conda run -n compliance-os python -m build 2>&1 | tail -3
unzip -l dist/compliance_os-2.0.2-py3-none-any.whl | grep -E "consent.py|document_chains.yaml|context.py"
```
Expected: wheel built; `compliance_os/consent.py`, `compliance_os/compliance/document_chains.yaml`, and `compliance_os/web/routers/context.py` all present.

- [ ] **Step 5: Rebuild the .dxt + verify pin**

Run:
```bash
conda run -n compliance-os python scripts/build_dxt.py
unzip -p frontend/public/guardian.dxt pyproject.toml | grep compliance-os
unzip -p frontend/public/guardian.dxt manifest.json | grep '"version"'
```
Expected: `compliance-os[agent]==2.0.2`; manifest version `2.0.2`.

- [ ] **Step 6: Upload to PyPI** — requires the PyPI token (ask the user; pass via env, do not persist):

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD='<token>' conda run -n compliance-os twine upload dist/compliance_os-2.0.2*
```
Expected: `View at: https://pypi.org/project/compliance-os/2.0.2/`. Then verify:
```bash
curl -s https://pypi.org/pypi/compliance-os/json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['info']['version'])"
```
Expected: `2.0.2`.

- [ ] **Step 7: Commit the release**

```bash
git add pyproject.toml compliance_os/__init__.py scripts/build_dxt.py frontend/public/guardian.dxt
git commit -m "release: 2.0.2 — share_data_room egress path + consent + context endpoint"
```

**Deploy note:** the server endpoint (`/api/context/share`) reaches production only via the Fly deploy. Fold this into the same deploy that ships Plan A (still blocked on the Docker/network environment). The PyPI 2.0.2 wheel + the re-pinned `.dxt` deliver the extension side.

---

## Self-Review Notes

**Spec coverage (§4):** consent store + management tools (Tasks 1, 3 — `list_egress_consents`/`revoke_egress_consent`) ✅; `share_data_room(purpose, confirm, remember)` reusing `export_user_data` (Task 2) ✅; per-purpose granularity (Tasks 1–3) ✅; `guardian_ask` grounding-only regression (Task 4) ✅; professional-search transparency note §4.4 (Task 5) ✅; `POST /api/context/share` + `SharedContextRow` §4.5 (Task 6) ✅; 2.0.2 release §8 (Task 7) ✅.

**Type consistency:** `has_consent(purpose)`, `record_consent(purpose, scope, *, destination, data_categories)`, `revoke_consent(purpose)`, `list_consents()` defined in Task 1 and used identically in Tasks 2–3. `local_share_data_room(purpose, confirm=False, remember="once") -> dict` with `status` in `{consent_required, shared}` consistent across Tasks 2–3. `_post_context_share(zip_bytes, purpose, token) -> dict` injectable for tests (Task 2) and monkeypatched in Task 3. `SharedContextRow {id, user_id, purpose, path, created_at}` defined Task 6, queried in its test.

**Known risks / verify-before-coding:**
- Task 6 uses placeholder-ish auth helpers (`create_token_for_user`, `UserRow(email=...)`); confirm the real names in `auth_service.py`/`models/auth.py` and adjust the test to the actual token-mint + user-create API before running. The endpoint itself only depends on the existing `get_bearer_payload`, which is verified to exist.
- Task 5: confirm `build_search_plan`'s return shape (dict vs list) and keep the `privacy_note` access path consistent between code and test.
- `share_data_room` egresses to `GUARDIAN_CLOUD_URL` (real prod), distinct from `GUARDIAN_API_URL` (in-process in local mode) — this is intentional and the one deliberate extension egress.
- Encryption-at-rest of the stored blob is deferred (spec §4.5 / §9); the endpoint stores token-gated per-user files. Do not claim at-rest encryption anywhere until implemented.
