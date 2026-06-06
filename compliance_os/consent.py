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
