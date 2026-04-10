"""Mailing and filing guidance for mail-dependent marketplace products."""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Mapping


FORM_8843_TAX_YEAR = 2025
FORM_8843_STANDALONE_DEADLINE = date(FORM_8843_TAX_YEAR + 1, 6, 15)
FORM_8843_TAX_PACKAGE_DEADLINE = date(FORM_8843_TAX_YEAR + 1, 4, 15)
FORM_8843_AUSTIN_ADDRESS = "\n".join(
    [
        "Department of the Treasury",
        "Internal Revenue Service Center",
        "Austin, TX 73301-0215",
    ]
)
FORM_8843_MAILING_SERVICE_PRICE_CENTS = 1900


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _deadline_label(value: date) -> str:
    return value.strftime("%B %d, %Y")


def _deadline_datetime(value: date) -> datetime:
    return datetime.combine(value, time(hour=16, minute=0), tzinfo=timezone.utc)


def _mailing_service_enabled() -> bool:
    return _truthy(os.environ.get("ENABLE_FORM_8843_MAILING_SERVICE"))


def build_form_8843_filing_context(inputs: Mapping[str, object]) -> dict[str, object]:
    """Return the filing guidance for a Form 8843 order."""
    filing_with_tax_return = _truthy(inputs.get("filing_with_tax_return")) or _truthy(inputs.get("has_us_income"))

    if filing_with_tax_return:
        deadline = FORM_8843_TAX_PACKAGE_DEADLINE
        steps = [
            "Download the generated Form 8843 and keep it with your Form 1040-NR package.",
            "Sign and date the return package where required before filing.",
            "Use your Form 1040-NR filing workflow and deadline rather than mailing Form 8843 by itself.",
            "If you mail the return, use tracked mail so you have proof of filing.",
        ]
        return {
            "scenario": "tax_return_package",
            "headline": "File this with your Form 1040-NR package",
            "summary": "Form 8843 should travel with your tax return package when you also need to file Form 1040-NR.",
            "filing_deadline": deadline,
            "deadline_label": _deadline_label(deadline),
            "address_block": "",
            "delivery_method": "download_only",
            "mailing_status": "not_required",
            "mail_required": False,
            "can_mark_mailed": False,
            "certified_mail_recommended": True,
            "steps": steps,
            "mailing_service_available": False,
            "mailing_service_price_cents": FORM_8843_MAILING_SERVICE_PRICE_CENTS,
            "mailing_service_note": "White-glove mailing does not apply when the form should be filed with a tax return package.",
        }

    deadline = FORM_8843_STANDALONE_DEADLINE
    steps = [
        "Print the PDF on standard paper.",
        "Sign and date the form before mailing it.",
        f"Mail it to:\n{FORM_8843_AUSTIN_ADDRESS}",
        "Use USPS Certified Mail with Return Receipt if possible so you have proof of filing.",
    ]
    mailing_service_enabled = _mailing_service_enabled()
    return {
        "scenario": "standalone_mail",
        "headline": "Print, sign, and mail your Form 8843",
        "summary": "Form 8843 by itself cannot be e-filed. Guardian can generate it for you, but you still need to mail the completed form.",
        "filing_deadline": deadline,
        "deadline_label": _deadline_label(deadline),
        "address_block": FORM_8843_AUSTIN_ADDRESS,
        "delivery_method": "user_mail",
        "mailing_status": "needs_signature",
        "mail_required": True,
        "can_mark_mailed": True,
        "certified_mail_recommended": True,
        "steps": steps,
        "mailing_service_available": mailing_service_enabled,
        "mailing_service_price_cents": FORM_8843_MAILING_SERVICE_PRICE_CENTS,
        "mailing_service_note": (
            "Guardian can only expose the assisted mailing option after signature and mailing operations are validated."
            if not mailing_service_enabled
            else "Guardian can help you route this into the assisted mailing flow."
        ),
    }


def serialize_filing_context(context: Mapping[str, object]) -> dict[str, object]:
    """Make filing context JSON-safe for persistence."""
    payload = dict(context)
    filing_deadline = payload.get("filing_deadline")
    if isinstance(filing_deadline, date):
        payload["filing_deadline"] = filing_deadline.isoformat()
    return payload


def build_form_8843_mailing_kit(context: Mapping[str, object]) -> dict[str, object]:
    """Build printable/copyable mailing kit details for the success flow."""
    address_block = str(context.get("address_block", "") or "").strip()
    steps = [str(step).strip() for step in context.get("steps", []) if str(step).strip()]
    filing_notes = "\n".join(steps)

    if not address_block:
        return {
            "address_block": "",
            "filing_notes": filing_notes or "File this with your Form 1040-NR package.",
            "mailing_label_text": "",
            "envelope_template_text": "",
            "recommended_service": "Tracked mail if you send the full tax package by post",
        }

    return {
        "address_block": address_block,
        "filing_notes": filing_notes,
        "mailing_label_text": address_block,
        "envelope_template_text": (
            "To:\n"
            f"{address_block}\n\n"
            "From:\n"
            "______________________________\n"
            "______________________________\n"
            "______________________________"
        ),
        "recommended_service": "USPS Certified Mail with Return Receipt",
    }


def next_mail_reminder_at(now: datetime | None = None) -> datetime:
    """Two-week reminder to confirm mailing completion."""
    current = now or datetime.now(timezone.utc)
    return current + timedelta(days=14)


def next_deadline_reminder_at(filing_deadline: date, now: datetime | None = None) -> datetime:
    """Thirty-day warning before the deadline, or immediate if already within that window."""
    current = now or datetime.now(timezone.utc)
    candidate = _deadline_datetime(filing_deadline - timedelta(days=30))
    return candidate if candidate > current else current
