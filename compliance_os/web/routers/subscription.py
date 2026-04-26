"""Guardian Pro subscription endpoints.

Three concerns:
  1. /checkout  — start a Stripe Checkout Session (mode=subscription) for
                   the Pro recurring price.
  2. /portal    — redirect into the Stripe Customer Portal so the user
                   manages their card / cancels themselves.
  3. /me        — read-only entitlement snapshot for the UI (tier, quota,
                   period_end, has_billing_portal flag).

Webhook handling for `customer.subscription.*` events lives in
professional_search.stripe_webhook (single webhook endpoint to keep
Stripe configuration simple). The router here only initiates flows.
"""
from __future__ import annotations

import datetime as _dt
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from compliance_os.settings import settings
from compliance_os.web.models.auth import SubscriptionRow, UserRow
from compliance_os.web.models.database import get_session
from compliance_os.web.services.auth_service import get_bearer_payload
from compliance_os.web.services.subscription_service import (
    FREE_EXTRACTIONS_PER_MONTH,
    PRO_FREE_SEARCHES_PER_PERIOD,
    get_active_subscription,
    get_extraction_quota,
    get_pro_search_quota,
    get_user_tier,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscription", tags=["subscription"])


def _get_user(authorization: str = Header(None), db: Session = Depends(get_session)) -> UserRow:
    payload = get_bearer_payload(authorization, db)
    user = db.query(UserRow).filter(UserRow.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _stripe():
    """Lazy-import Stripe; mirrors professional_search._stripe()."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured — STRIPE_SECRET_KEY is not set",
        )
    if not settings.stripe_pro_price_id:
        raise HTTPException(
            status_code=503,
            detail="Pro pricing not configured — STRIPE_PRO_PRICE_ID is not set",
        )
    import stripe as _s

    _s.api_key = settings.stripe_secret_key
    return _s


# ---------------------------- Checkout ----------------------------


class CheckoutRequest(BaseModel):
    # Optional: where to send the user back after success / cancel. Defaults
    # to /dashboard on success, /pricing on cancel.
    success_path: str | None = None
    cancel_path: str | None = None
    # Optional: pre-attach a free trial so the user sees "Free for N days,
    # then $20/mo" on the Stripe checkout page instead of "$20/mo today".
    # Used by the post-search-payment trial CTA when the saved-card path
    # fails (no setup_future_usage on the original purchase) — same trial
    # offer, fresh card. Stripe rejects trials for users who've already
    # had one on this customer, so pass-through is safe.
    trial_period_days: int | None = None


@router.post("/checkout")
def create_subscription_checkout(
    body: CheckoutRequest | None = None,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
):
    """Start a $20/mo Pro subscription checkout.

    If the user already has an active sub (paid or trialing), short-
    circuit to the Billing Portal instead — preventing duplicate
    subscriptions on the same customer.
    """
    body = body or CheckoutRequest()
    existing = get_active_subscription(user, db)
    if existing is not None and existing.tier == "pro":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "already_subscribed",
                "message": "You already have an active Pro subscription. Manage it in the billing portal.",
            },
        )

    stripe = _stripe()
    success_path = body.success_path or "/dashboard?subscribed=1"
    cancel_path = body.cancel_path or "/pricing?canceled=1"

    # Reuse existing Stripe customer if we know it (e.g. from a prior
    # lawyer-search payment), otherwise let Checkout create one and we'll
    # link it via the webhook.
    customer_kwargs: dict = {}
    if existing is not None and existing.stripe_customer_id:
        customer_kwargs["customer"] = existing.stripe_customer_id
    else:
        customer_kwargs["customer_email"] = user.email

    subscription_data: dict = {
        "metadata": {"user_id": user.id, "kind": "pro_subscription"},
    }
    if body.trial_period_days and body.trial_period_days > 0:
        subscription_data["trial_period_days"] = int(body.trial_period_days)
        # Match the saved-card trial behaviour: if no card lands by trial
        # end, cancel rather than fail to charge. Belt-and-suspenders since
        # Checkout already collects a card upfront for subscription mode.
        subscription_data["trial_settings"] = {
            "end_behavior": {"missing_payment_method": "cancel"}
        }

    try:
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
            success_url=f"{settings.public_app_url}{success_path}",
            cancel_url=f"{settings.public_app_url}{cancel_path}",
            client_reference_id=user.id,
            metadata={"user_id": user.id, "kind": "pro_subscription"},
            subscription_data=subscription_data,
            **customer_kwargs,
        )
    except Exception as exc:
        logger.exception("subscription checkout creation failed for user %s", user.id)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}")

    return {"url": checkout.url, "session_id": checkout.id}


# ---------------------------- Billing Portal ----------------------------


class PortalRequest(BaseModel):
    return_path: str | None = None


@router.post("/portal")
def create_billing_portal_session(
    body: PortalRequest | None = None,
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
):
    """Redirect the user into the Stripe Customer Portal.

    Requires a Stripe Customer ID — without one we have nothing to manage,
    so we 404 and let the UI route to /pricing instead.
    """
    body = body or PortalRequest()
    sub = get_active_subscription(user, db)
    customer_id = sub.stripe_customer_id if sub is not None else None
    if not customer_id:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "no_billing_record",
                "message": "No billing history yet. Subscribe first.",
            },
        )

    stripe = _stripe()
    return_url = f"{settings.public_app_url}{body.return_path or '/dashboard'}"
    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    except Exception as exc:
        logger.exception("billing portal creation failed for user %s", user.id)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}")
    return {"url": portal.url}


# ---------------------------- Read state ----------------------------


@router.get("/me")
def get_subscription_state(
    user: UserRow = Depends(_get_user),
    db: Session = Depends(get_session),
):
    """Return everything the UI needs to render the upgrade / quota state.

    No PII beyond what the user already knows (their email is theirs).
    Numbers are derived live so the badge is always fresh.
    """
    tier = get_user_tier(user, db)
    sub = get_active_subscription(user, db)
    extraction = get_extraction_quota(user, db)
    pro_search = get_pro_search_quota(user, db)

    return {
        "tier": tier,
        "is_pro": tier in ("pro", "pro_trial"),
        "is_paying_pro": tier == "pro",
        "subscription": (
            {
                "status": sub.status,
                "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                "current_period_end": (
                    sub.current_period_end.isoformat() if sub.current_period_end else None
                ),
                "cancel_at_period_end": bool(sub.cancel_at_period_end),
                "has_billing_portal": bool(sub.stripe_customer_id),
            }
            if sub is not None
            else None
        ),
        "extraction_quota": {
            "used": extraction.used,
            "limit": extraction.limit,
            "remaining": extraction.remaining,
            "at_limit": extraction.at_limit,
            "reset_at": extraction.reset_at.isoformat() if extraction.reset_at else None,
        },
        "pro_search_quota": {
            "used": pro_search.used,
            "limit": pro_search.limit,
            "has_free_search": pro_search.has_free_search,
            "period_end": (
                pro_search.period_end.isoformat() if pro_search.period_end else None
            ),
        },
        "limits": {
            "free_extractions_per_month": FREE_EXTRACTIONS_PER_MONTH,
            "pro_free_searches_per_period": PRO_FREE_SEARCHES_PER_PERIOD,
        },
    }
