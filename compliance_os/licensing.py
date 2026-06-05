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
    if grace_until is None:
        # Server returned no expiry or cache was written without grace_until;
        # fall back to a grace window computed from when the cache was written.
        cached_at = _parse_dt(ent.get("_cached_at"))
        if cached_at is not None:
            grace_until = cached_at + timedelta(hours=_REFRESH_AFTER_HOURS * 7)
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
