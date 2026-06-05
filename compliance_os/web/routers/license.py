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
