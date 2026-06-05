# License / Entitlements Control Plane Implementation Plan (Plan 3 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the local Guardian extension on a Guardian-issued license key — no valid key, the extension does nothing — while reusing the existing `gdn_oc_` token + `subscriptions` infrastructure. Adds a server `/api/license/validate` endpoint, a client-side activation cache + state machine with offline grace, and a single `GatedMCP.call_tool` override that enforces activation across all 33 MCP tools without per-tool edits.

**Architecture:** The license key IS the existing `gdn_oc_` API token (`issue_openclaw_token`). The server endpoint resolves it via `decode_token` → user → `get_user_tier`, returning `{valid, status, tier, features, grace_until}`. The client (`compliance_os/licensing.py`) validates online (startup/stale), caches entitlements in `~/.guardian/license.json`, and computes an activation state honoring a grace window. Gating is centralized by subclassing `FastMCP`: `GatedMCP.call_tool` checks activation **only in standalone mode** (`not _is_hosted()`) and returns a structured `activation_required` message instead of raising. The hosted `/mcp` mount and the existing test suite (which call tool functions directly, bypassing `call_tool`) are unaffected.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, FastMCP (`mcp` 1.27), `urllib` (no new deps), pytest.

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-04-local-first-compliance-loop-design.md` (§ License / Entitlements Control Plane)
- `compliance_os/web/services/auth_service.py` — `decode_token(token, db)` (raises `HTTPException(401)` on bad token), `issue_openclaw_token(user, db) -> (UserApiTokenRow, raw_token)`
- `compliance_os/web/services/subscription_service.py` — `get_user_tier(user, db) -> "free"|"pro_trial"|"pro"`
- `compliance_os/web/models/auth.py` — `UserRow`, `SubscriptionRow`
- `compliance_os/web/app.py:94-116` — `app.include_router(...)` block
- `compliance_os/mcp_server.py:21-38` — `from mcp.server.fastmcp import FastMCP`; `mcp = FastMCP("guardian", instructions=...)`; `_is_hosted()` (~line 211)
- FastMCP `call_tool(self, name, arguments) -> Sequence[ContentBlock] | dict` is overridable; `mcp.types.TextContent` is the result block type.

---

## File Structure

- **Create** `compliance_os/web/routers/license.py` — the `/api/license/validate` endpoint + `features_for_tier`.
- **Modify** `compliance_os/web/app.py` — register the license router.
- **Create** `compliance_os/licensing.py` — client activation: `validate_online`, cache I/O, `activation_state`, `activation_block`, `feature_for_tool`.
- **Modify** `compliance_os/mcp_server.py` — `GatedMCP(FastMCP)` subclass; construct `mcp` from it.
- **Create** `tests/test_license.py` — server endpoint, client state machine, and the gate.

---

## Task 1: Server `/api/license/validate` endpoint

**Files:**
- Create: `compliance_os/web/routers/license.py`
- Modify: `compliance_os/web/app.py`
- Test: `tests/test_license.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_license.py
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def local_db(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    yield database
    database._engine = None
    database._SessionLocal = None


def _make_user_with_token(db):
    import secrets as _secrets
    from compliance_os.web.models.auth import UserRow
    from compliance_os.web.services.auth_service import issue_openclaw_token

    user = UserRow(email=f"u{_secrets.token_hex(4)}@x.com", password_hash="x", role="user")
    db.add(user)
    db.commit()
    _row, raw = issue_openclaw_token(user, db)
    db.commit()
    return user, raw


def test_validate_known_key_returns_active_free(local_db):
    from compliance_os.web.routers.license import ValidateRequest, validate

    db = next(local_db.get_session())
    try:
        _user, key = _make_user_with_token(db)
        out = validate(ValidateRequest(license_key=key, ext_version="2.0.0"), db=db)
        assert out["valid"] is True
        assert out["status"] == "active"
        assert out["tier"] == "free"
        assert "extraction" in out["features"]
        assert out["grace_until"]  # an ISO timestamp
    finally:
        db.close()


def test_validate_bad_key_is_invalid(local_db):
    from compliance_os.web.routers.license import ValidateRequest, validate

    db = next(local_db.get_session())
    try:
        out = validate(ValidateRequest(license_key="gdn_oc_dead_beef"), db=db)
        assert out["valid"] is False
        assert out["status"] == "invalid"
        assert out["features"] == []
    finally:
        db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_license.py::test_validate_known_key_returns_active_free -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.web.routers.license'`.

- [ ] **Step 3: Create the license router**

Create `compliance_os/web/routers/license.py`:

```python
"""License / entitlements validation for the local Guardian extension.

The local extension posts its license key (the user's gdn_oc_ token) here
on activation + periodically. We resolve it to a user, read their tier from
the existing subscriptions mirror, and return the entitlements the client
caches. This is the ONLY server touchpoint for the free local product, and
it carries no user document data — only the key + extension version.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.services.auth_service import decode_token
from compliance_os.web.services.subscription_service import get_user_tier

router = APIRouter(prefix="/api/license", tags=["license"])

GRACE_DAYS = 7

# Free tier ships with everything ON (distribute-first). Pro is a superset
# placeholder for future server-reserved features. Flipping a feature to
# pro-only later is a change here — no client re-ship.
_BASE_FEATURES = ["extraction", "chat", "facts", "documents", "prof_search", "gmail_draft"]
_PRO_EXTRAS = ["prof_search_cloud", "sync"]


def features_for_tier(tier: str) -> list[str]:
    if tier in ("pro", "pro_trial"):
        return _BASE_FEATURES + _PRO_EXTRAS
    return list(_BASE_FEATURES)


class ValidateRequest(BaseModel):
    license_key: str
    ext_version: str = ""


def _invalid() -> dict:
    return {
        "valid": False,
        "status": "invalid",
        "tier": "free",
        "features": [],
        "grace_until": None,
        "message": "License key not recognized. Get yours at https://guardiancompliance.app/connect.",
    }


@router.post("/validate")
def validate(req: ValidateRequest, db: Session = Depends(get_session)) -> dict:
    """Resolve a license key to its entitlements. Carries no user data."""
    try:
        payload = decode_token(req.license_key, db)
    except HTTPException:
        return _invalid()
    user = db.query(UserRow).filter(UserRow.id == payload.get("user_id")).first()
    if user is None:
        return _invalid()
    tier = get_user_tier(user, db)
    db.commit()  # persist last_used_at touched by token auth
    grace_until = (datetime.now(timezone.utc) + timedelta(days=GRACE_DAYS)).isoformat()
    return {
        "valid": True,
        "status": "active",
        "tier": tier,
        "features": features_for_tier(tier),
        "grace_until": grace_until,
        "message": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_license.py::test_validate_known_key_returns_active_free tests/test_license.py::test_validate_bad_key_is_invalid -v`
Expected: PASS (both).

- [ ] **Step 5: Register the router in `app.py`**

In `compliance_os/web/app.py`, add an import alongside the other router imports (near the top where `user_facts_router` is imported):

```python
from compliance_os.web.routers import license as license_router
```

And add this line right after `app.include_router(user_facts_router.router)` (around line 116):

```python
app.include_router(license_router.router)
```

- [ ] **Step 6: Verify the route is mounted + commit**

```python
def test_license_route_is_registered():
    from compliance_os.web.app import app

    paths = {r.path for r in app.routes}
    assert "/api/license/validate" in paths
```

Run: `pytest tests/test_license.py -q`
Expected: PASS (3 tests).

```bash
git add compliance_os/web/routers/license.py compliance_os/web/app.py tests/test_license.py
git commit -m "feat(license): /api/license/validate endpoint reusing gdn_oc_ token + tier"
```

---

## Task 2: Client activation module (`licensing.py`)

**Files:**
- Create: `compliance_os/licensing.py`
- Test: `tests/test_license.py`

- [ ] **Step 1: Write the failing test**

```python
def test_unconfigured_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    assert licensing.activation_state() == "unconfigured"
    block = licensing.activation_block()
    assert block is not None and block["state"] == "unconfigured"


def test_active_when_online_validates(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": True, "status": "active", "tier": "free",
                     "features": ["extraction", "chat"], "grace_until": None},
    )
    assert licensing.activation_state() == "active"
    assert licensing.activation_block() is None


def test_inactive_when_server_says_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": False, "status": "invalid", "tier": "free",
                     "features": [], "grace_until": None},
    )
    assert licensing.activation_state() == "inactive"
    assert licensing.activation_block()["state"] == "inactive"


def test_offline_grace_then_expiry(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing

    # Offline: validate_online returns None; fall back to cache.
    monkeypatch.setattr(licensing, "validate_online", lambda key: None)

    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    licensing._write_cache({"valid": True, "status": "active", "tier": "free",
                            "features": ["extraction"], "grace_until": future})
    assert licensing.activation_state() == "active"   # within grace

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    licensing._write_cache({"valid": True, "status": "active", "tier": "free",
                            "features": ["extraction"], "grace_until": past})
    assert licensing.activation_state() == "expired_offline"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_license.py::test_unconfigured_without_key -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'compliance_os.licensing'`.

- [ ] **Step 3: Create `compliance_os/licensing.py`**

```python
"""Client-side license activation for the local Guardian extension.

No valid key → the extension does nothing. We validate the key against
Guardian's tiny /api/license/validate endpoint on startup and when the
cache is stale, cache the entitlements under ~/.guardian/license.json,
and honor an offline grace window so brief offline use still works. The
only thing sent out is the key + extension version — never user data.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import request as _urlrequest

EXT_VERSION = "2.0.0"
DEFAULT_VALIDATE_URL = "https://guardiancompliance.app/api/license/validate"
_REFRESH_AFTER_HOURS = 24

# Tools that require a specific entitlement feature. Empty/absent → no
# feature gate (v1 ships everything on). Flipping a tool to require a
# pro-only feature later is a one-line change here.
TOOL_FEATURES: dict[str, str] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _license_key() -> str:
    return (
        os.environ.get("GUARDIAN_LICENSE_KEY")
        or os.environ.get("GUARDIAN_TOKEN")
        or ""
    ).strip()


def _validate_url() -> str:
    return os.environ.get("GUARDIAN_LICENSE_VALIDATE_URL") or DEFAULT_VALIDATE_URL


def _cache_path() -> Path:
    home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
    return home / "license.json"


def feature_for_tool(tool_name: str) -> str | None:
    return TOOL_FEATURES.get(tool_name)


def validate_online(key: str) -> dict | None:
    """POST the key to the validate endpoint. Returns entitlements dict, or
    None if unreachable. Sends only the key + extension version."""
    payload = json.dumps({"license_key": key, "ext_version": EXT_VERSION}).encode()
    req = _urlrequest.Request(
        _validate_url(), data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with _urlrequest.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _read_cache() -> dict | None:
    try:
        return json.loads(_cache_path().read_text())
    except Exception:
        return None


def _write_cache(entitlements: dict) -> None:
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(entitlements)
        data["_cached_at"] = _now().isoformat()
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _parse_dt(value) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _should_refresh(cache: dict | None) -> bool:
    if not cache:
        return True
    cached_at = _parse_dt(cache.get("_cached_at"))
    if cached_at is None:
        return True
    return (_now() - cached_at) > timedelta(hours=_REFRESH_AFTER_HOURS)


def current_entitlements() -> dict | None:
    """Entitlements for the configured key: refresh online when stale, else
    fall back to cache. None when no key is configured."""
    key = _license_key()
    if not key:
        return None
    cache = _read_cache()
    if _should_refresh(cache):
        fresh = validate_online(key)
        if fresh is not None:
            _write_cache(fresh)
            return fresh
    return cache


def activation_state() -> str:
    """One of: unconfigured | active | inactive | expired_offline."""
    key = _license_key()
    if not key:
        return "unconfigured"
    cache = _read_cache()
    fresh = None
    if _should_refresh(cache):
        fresh = validate_online(key)
        if fresh is not None:
            _write_cache(fresh)
    ent = fresh if fresh is not None else cache
    if ent is None:
        # Key set but never validated and currently offline.
        return "expired_offline"
    if not ent.get("valid"):
        return "inactive"
    if fresh is not None:
        return "active"  # confirmed online just now
    grace_until = _parse_dt(ent.get("grace_until"))
    if grace_until is not None and _now() <= grace_until:
        return "active"  # offline but within grace
    return "expired_offline"


_MESSAGES = {
    "unconfigured": "Configure your Guardian license key (GUARDIAN_LICENSE_KEY) to activate. Get one at https://guardiancompliance.app/connect.",
    "inactive": "Your Guardian license is inactive. Reactivate at https://guardiancompliance.app/account.",
    "expired_offline": "Reconnect to the internet to reactivate Guardian (offline grace expired).",
}


def activation_block(feature: str | None = None) -> dict | None:
    """Return an activation-required message dict if the extension is not
    usable, else None. feature gating is a no-op until a tool is mapped to a
    pro-only feature in TOOL_FEATURES + that feature is withheld server-side."""
    state = activation_state()
    if state != "active":
        return {
            "error": "activation_required",
            "state": state,
            "message": _MESSAGES.get(state, _MESSAGES["inactive"]),
        }
    if feature:
        ent = current_entitlements() or {}
        if feature not in (ent.get("features") or []):
            return {
                "error": "feature_locked",
                "feature": feature,
                "message": f"'{feature}' requires an upgrade. See https://guardiancompliance.app/account.",
            }
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_license.py -k "unconfigured or active_when or inactive_when or offline_grace" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add compliance_os/licensing.py tests/test_license.py
git commit -m "feat(license): client activation module (validate, cache, state machine, grace)"
```

---

## Task 3: `GatedMCP` — enforce activation on every tool (standalone only)

**Files:**
- Modify: `compliance_os/mcp_server.py`
- Test: `tests/test_license.py`

- [ ] **Step 1: Write the failing test**

```python
def test_gate_blocks_unconfigured_standalone(monkeypatch, tmp_path):
    """In standalone mode with no key, dispatching any tool returns the
    activation message instead of running the tool."""
    import asyncio

    monkeypatch.delenv("GUARDIAN_LICENSE_KEY", raising=False)
    monkeypatch.delenv("GUARDIAN_TOKEN", raising=False)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import mcp_server

    def _run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(asyncio.new_event_loop())

    result = _run(mcp_server.mcp.call_tool("get_extraction_schema", {"doc_type": "i20"}))
    text = result[0].text if isinstance(result, (list, tuple)) else json.dumps(result)
    assert "activation_required" in text


def test_gate_allows_when_active(monkeypatch, tmp_path):
    import asyncio

    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", "gdn_oc_aa_bb")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import licensing, mcp_server

    monkeypatch.setattr(
        licensing, "validate_online",
        lambda key: {"valid": True, "status": "active", "tier": "free",
                     "features": ["extraction", "chat", "facts", "documents"],
                     "grace_until": None},
    )

    def _run(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(asyncio.new_event_loop())

    result = _run(mcp_server.mcp.call_tool("get_extraction_schema", {"doc_type": "i20"}))
    text = result[0].text if isinstance(result, (list, tuple)) else json.dumps(result)
    assert "activation_required" not in text
    assert "sevis_id" in text  # the real tool ran
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_license.py::test_gate_blocks_unconfigured_standalone -v`
Expected: FAIL — the tool runs and returns the schema (no gate yet), so `"activation_required"` is absent.

- [ ] **Step 3: Add `GatedMCP` and construct `mcp` from it**

In `compliance_os/mcp_server.py`, add the import near the top (with the other `mcp`/licensing imports):

```python
from mcp.types import TextContent
from compliance_os.licensing import activation_block, feature_for_tool
```

Replace the `mcp = FastMCP(...)` construction with a gated subclass. Find:

```python
mcp = FastMCP(
    "guardian",
    instructions=(
        ...
    ),
)
```

and change `FastMCP(` to `GatedMCP(`, adding the class definition immediately above it:

```python
class GatedMCP(FastMCP):
    """FastMCP that gates every tool dispatch on license activation when
    running as the standalone local extension. The hosted /mcp mount
    (where users authenticate per-request) is never gated, and direct
    function calls (tests, internal use) bypass this entirely."""

    async def call_tool(self, name, arguments):
        if not _is_hosted():
            block = activation_block(feature_for_tool(name))
            if block is not None:
                return [TextContent(type="text", text=json.dumps(block))]
        return await super().call_tool(name, arguments)


mcp = GatedMCP(
    "guardian",
    instructions=(
        ...
    ),
)
```

(Keep the existing `instructions=...` content unchanged — only the class name changes and the subclass is added. `_is_hosted` is defined later in the module and resolved at call time, so the forward reference is fine.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_license.py::test_gate_blocks_unconfigured_standalone tests/test_license.py::test_gate_allows_when_active -v`
Expected: PASS (both).

- [ ] **Step 5: Confirm existing tests still bypass the gate + commit**

The Plan 1/2 tests call tool functions directly (e.g. `mcp_server.get_user_facts()`), which does NOT go through `call_tool`, so the gate doesn't touch them. Verify:

Run: `pytest tests/test_local_engine.py tests/test_extraction_rehome.py tests/test_mcp_server.py -q`
Expected: PASS (no new failures — same as before this task).

```bash
git add compliance_os/mcp_server.py tests/test_license.py
git commit -m "feat(license): GatedMCP enforces activation on every tool in standalone mode"
```

---

## Task 4: End-to-end + regression sweep

**Files:**
- Test: `tests/test_license.py`

- [ ] **Step 1: Write the full-cycle test**

```python
def test_license_end_to_end(local_db, monkeypatch, tmp_path):
    """Server issues entitlements for a real key; client caches + activates;
    the gate then lets a tool run."""
    import asyncio
    from compliance_os import licensing
    from compliance_os.web.routers.license import ValidateRequest, validate

    # Server side: a real user + key resolves to active/free entitlements.
    db = next(local_db.get_session())
    try:
        _user, key = _make_user_with_token(db)
        server_out = validate(ValidateRequest(license_key=key), db=db)
    finally:
        db.close()
    assert server_out["valid"] and "extraction" in server_out["features"]

    # Client side: point validate_online at the in-process server result.
    monkeypatch.setenv("GUARDIAN_LICENSE_KEY", key)
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.setattr(licensing, "validate_online", lambda k: server_out)
    assert licensing.activation_state() == "active"
    assert licensing.activation_block() is None
```

- [ ] **Step 2: Run the full module**

Run: `pytest tests/test_license.py -v`
Expected: PASS (10 tests).

- [ ] **Step 3: Regression sweep**

Run: `pytest tests/ -q`
Expected: only the pre-existing 13 failures (`test_election_83b`, `marketplace`, `auth`, `cases_router`, `database`). Confirm zero failures in the new/local modules:
`pytest tests/ -q 2>&1 | grep -E "FAILED tests/(test_mcp_server|test_local_engine|test_extraction_rehome|test_license)"` → must be empty.

- [ ] **Step 4: Commit**

```bash
git add tests/test_license.py
git commit -m "test(license): end-to-end server→client→gate activation cycle"
```

---

## Self-Review Notes

**Spec coverage (§ License / Entitlements Control Plane):**
- License key required to operate → Task 3 gate (`unconfigured` → blocked).
- `POST /api/license/validate {license_key, ext_version}` reusing `subscriptions`/tier → Task 1.
- Cache in `~/.guardian/license.json` + offline grace state machine → Task 2.
- `@requires_activation` (global) → centralized in `GatedMCP.call_tool` (Task 3); `@requires_feature` → `feature_for_tool` + `TOOL_FEATURES` hook (no-op in v1, everything on).
- Structured `activation_required` message, not an exception → Task 3 returns a `TextContent` with the block JSON.
- Privacy invariant: only key + version sent → `validate_online` payload (Task 2).

**Key design decisions (documented so they aren't mistaken for bugs):**
- The license key IS the existing `gdn_oc_` token — no new key type. The DXT's `license_key` config holds it; `licensing._license_key()` also falls back to `GUARDIAN_TOKEN` for migration.
- The gate fires **only when `not _is_hosted()`** — the hosted `/mcp` mount and the entire existing test suite (direct function calls) are deliberately unaffected. Tests exercise the gate via `mcp.call_tool(...)`.
- Status collapses `revoked` into `invalid`/`valid=false` for v1 (revoked tokens have `revoked_at` set → `authenticate_api_token` raises → `_invalid()`); the client treats `valid=false` as `inactive`. A distinct `revoked` status is a future refinement.

**Type consistency:** server `validate` returns `{valid, status, tier, features, grace_until, message}`; client caches that shape verbatim and reads `valid`, `features`, `grace_until`. `activation_block` returns `{error, state, message}` or `{error, feature, message}` or `None`. `feature_for_tool(name) -> str | None`.

**Scope (Plan 3 of 4):** no Gmail/packaging (Plan 4). No payment/checkout flow (YAGNI — the entitlement hook exists; flipping features to pro-only is a future server-side change). Reuses Plan 1/2 plumbing only indirectly (the gate is independent of local-mode data adapters).

**Known risks to watch during implementation:**
- The `mcp = GatedMCP(...)` construction must preserve the existing `instructions=...` text exactly — only the class changes. If `_is_hosted` is not yet importable/defined at call time in some path, the gate would error; it is a module-level function resolved lazily, so confirm `mcp.call_tool` works in the test.
- `validate` touches `last_used_at` via `decode_token`; the `db.commit()` persists it. In the test, the `_make_user_with_token` helper commits the token first so the lookup succeeds.
- If `app.py` import of the license router triggers a circular import (it imports `auth_service` + `subscription_service`, already imported elsewhere), keep the import at the top with the other routers — they share the same dependency graph and load fine.
