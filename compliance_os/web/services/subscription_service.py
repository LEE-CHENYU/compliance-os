"""Subscription state, entitlement checks, and quota accounting.

Source of truth for tier/status/period bookkeeping is Stripe — this
module reads from `subscriptions` (a webhook-driven mirror) and never
mutates Stripe directly. Mutations happen in the subscription router
and webhook handlers.

Quotas (single source of truth — change here):

  Free tier:    FREE_EXTRACTIONS_PER_MONTH extractions per calendar month
  Pro tier:     unlimited extractions; PRO_FREE_SEARCHES_PER_PERIOD lawyer
                search per Stripe billing period; additional searches use
                the same $15 SKU as Free users
  Pro Trial:    unlimited extractions; NO free lawyer searches (trial is
                the data-room benefit only — paid Pro is the search benefit)
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from compliance_os.web.models.auth import SubscriptionRow, UserRow
from compliance_os.web.models.tables import ProfessionalSearchRequestRow
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow

# Tunables — only knob the business cares about.
FREE_EXTRACTIONS_PER_MONTH = 10
PRO_FREE_SEARCHES_PER_PERIOD = 1


@dataclass(frozen=True)
class ExtractionQuota:
    used: int
    limit: int | None  # None means unlimited
    tier: str          # 'free' | 'pro_trial' | 'pro'
    reset_at: _dt.datetime | None  # for Free: 1st of next month UTC

    @property
    def remaining(self) -> int | None:
        if self.limit is None:
            return None
        return max(0, self.limit - self.used)

    @property
    def at_limit(self) -> bool:
        return self.limit is not None and self.used >= self.limit


@dataclass(frozen=True)
class ProSearchQuota:
    used: int
    limit: int | None        # None = not eligible (Free / Trial)
    period_end: _dt.datetime | None

    @property
    def has_free_search(self) -> bool:
        return self.limit is not None and self.used < self.limit


def _start_of_next_month(now: _dt.datetime) -> _dt.datetime:
    if now.month == 12:
        return _dt.datetime(now.year + 1, 1, 1)
    return _dt.datetime(now.year, now.month + 1, 1)


def get_active_subscription(user: UserRow, db: Session) -> SubscriptionRow | None:
    """Return the user's currently-entitled subscription, or None.

    "Active" means Stripe status is trialing/active/past_due. We keep
    canceled rows for audit, but they grant nothing. If the user has
    multiple historical rows we return the most recent one (Stripe
    enforces one active sub per customer at most for our product).
    """
    return (
        db.query(SubscriptionRow)
        .filter(
            SubscriptionRow.user_id == user.id,
            SubscriptionRow.status.in_(("trialing", "active", "past_due")),
        )
        .order_by(SubscriptionRow.created_at.desc())
        .first()
    )


def get_user_tier(user: UserRow, db: Session) -> str:
    """Return 'free' | 'pro_trial' | 'pro'.

    `tier` is mirrored on SubscriptionRow at webhook write-time so we
    don't recompute it on every request. Trust it.
    """
    sub = get_active_subscription(user, db)
    if sub is None:
        return "free"
    return sub.tier


def is_pro(user: UserRow, db: Session) -> bool:
    """True if user has any active entitlement (Pro OR Pro trial).

    Use this for features that BOTH tiers unlock — namely unlimited
    extractions. Do NOT use for the lawyer-search free-pass; trial
    users must still pay $15 per search.
    """
    return get_active_subscription(user, db) is not None


def is_paying_pro(user: UserRow, db: Session) -> bool:
    """True if user is on paid Pro (NOT trial).

    Use for the lawyer-search free-pass — trial users don't qualify.
    """
    sub = get_active_subscription(user, db)
    return sub is not None and sub.tier == "pro"


def _count_extractions_this_month(user: UserRow, db: Session) -> int:
    """Count v2 documents uploaded this calendar month for this user.

    Each upload triggers OCR + structured extraction (paid LLM calls),
    so document count == extraction event count regardless of whether
    extraction succeeded — failures still cost. Joining on CheckRow
    because v2 docs scope through checks, not directly to users.
    """
    now = _dt.datetime.utcnow()
    start = _dt.datetime(now.year, now.month, 1)
    return (
        db.query(func.count(DocumentRow.id))
        .join(CheckRow, DocumentRow.check_id == CheckRow.id)
        .filter(
            CheckRow.user_id == user.id,
            DocumentRow.uploaded_at >= start,
        )
        .scalar()
        or 0
    )


def get_extraction_quota(user: UserRow, db: Session) -> ExtractionQuota:
    """Compute current-month extraction usage and remaining quota."""
    tier = get_user_tier(user, db)
    used = _count_extractions_this_month(user, db)
    if tier in ("pro", "pro_trial"):
        return ExtractionQuota(used=used, limit=None, tier=tier, reset_at=None)
    return ExtractionQuota(
        used=used,
        limit=FREE_EXTRACTIONS_PER_MONTH,
        tier="free",
        reset_at=_start_of_next_month(_dt.datetime.utcnow()),
    )


def get_pro_search_quota(user: UserRow, db: Session) -> ProSearchQuota:
    """Compute current-period Pro free-lawyer-search consumption.

    Returns limit=None for Free + Trial users (they don't get the perk).
    For paid Pro users, counts professional_search_requests rows whose
    `pro_free_grant_at` falls within the active subscription period.
    """
    sub = get_active_subscription(user, db)
    if sub is None or sub.tier != "pro":
        return ProSearchQuota(used=0, limit=None, period_end=None)

    period_start = sub.current_period_start
    if period_start is None:
        # Defensive — Pro sub without period dates means webhook hasn't
        # populated them yet. Surface limit=1 but used=0 so the user
        # isn't blocked; if they grab the free search before Stripe
        # finishes wiring up, we still record pro_free_grant_at, and
        # the next period's count will see it.
        return ProSearchQuota(
            used=0,
            limit=PRO_FREE_SEARCHES_PER_PERIOD,
            period_end=sub.current_period_end,
        )

    used = (
        db.query(func.count(ProfessionalSearchRequestRow.id))
        .filter(
            ProfessionalSearchRequestRow.user_id == user.id,
            ProfessionalSearchRequestRow.pro_free_grant_at.isnot(None),
            ProfessionalSearchRequestRow.pro_free_grant_at >= period_start,
        )
        .scalar()
        or 0
    )
    return ProSearchQuota(
        used=used,
        limit=PRO_FREE_SEARCHES_PER_PERIOD,
        period_end=sub.current_period_end,
    )


def enforce_extraction_quota(user: UserRow, db: Session) -> ExtractionQuota:
    """Raise 402 if the user has hit their extraction limit; else return the quota.

    Centralized so every paid-extraction route returns the same JSON shape
    to the UI. The frontend's paywall modal keys on `code` to distinguish
    quota-exceeded from other 402 reasons.
    """
    from fastapi import HTTPException

    quota = get_extraction_quota(user, db)
    if quota.at_limit:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "extraction_quota_exceeded",
                "tier": quota.tier,
                "used": quota.used,
                "limit": quota.limit,
                "reset_at": quota.reset_at.isoformat() if quota.reset_at else None,
                "upgrade_url": "/pricing",
                "message": (
                    f"You've used {quota.used} of {quota.limit} free extractions "
                    f"this month. Upgrade to Pro for unlimited extractions."
                ),
            },
        )
    return quota


def derive_tier(stripe_status: str) -> str:
    """Map Stripe subscription.status → our tier label.

    `trialing` → `pro_trial` (entitled to extractions, NOT free searches)
    everything else (active / past_due) → `pro`
    Canceled / incomplete / unpaid → caller should drop the row from
    the active-sub query, not store as Pro.
    """
    return "pro_trial" if stripe_status == "trialing" else "pro"
