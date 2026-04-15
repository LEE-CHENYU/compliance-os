"""83(b) election packet generation."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.services.pdf_builder import build_text_pdf


ELECTION_83B_DIR = DATA_DIR / "marketplace" / "election_83b"


# Simplified state → IRS service center mapping for 83(b) elections.
# 83(b) goes to the service center where the taxpayer files Form 1040.
# Source: IRS "Where to File Paper Tax Returns" (2024), individual filers.
_STATE_TO_SERVICE_CENTER: dict[str, str] = {
    # Austin, TX (no-payment address for 1040 from these states)
    **dict.fromkeys(["FL", "LA", "MS", "TX"], "austin"),
    # Kansas City, MO
    **dict.fromkeys(
        ["AR", "CT", "DE", "IL", "IN", "MA", "MD", "ME", "MI", "MN", "NH",
         "NJ", "NY", "OH", "PA", "RI", "VT", "WI", "WV"],
        "kansas_city",
    ),
    # Ogden, UT
    **dict.fromkeys(
        ["AK", "AZ", "CA", "CO", "HI", "ID", "IA", "KS", "MO", "MT", "NE",
         "NV", "NM", "ND", "OK", "OR", "SD", "UT", "WA", "WY"],
        "ogden",
    ),
    # Austin, TX (Southeast cluster as of 2024)
    **dict.fromkeys(["AL", "GA", "KY", "NC", "SC", "TN", "VA", "DC"], "austin"),
}

_SERVICE_CENTER_ADDRESSES: dict[str, tuple[str, str]] = {
    "austin": (
        "Internal Revenue Service",
        "Austin, TX 73301-0002",
    ),
    "kansas_city": (
        "Internal Revenue Service",
        "Kansas City, MO 64999-0002",
    ),
    "ogden": (
        "Internal Revenue Service",
        "Ogden, UT 84201-0002",
    ),
}

_STATE_ABBREV_RE = re.compile(r"\b([A-Z]{2})\s+\d{5}")


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _infer_service_center(taxpayer_address: str) -> tuple[str | None, tuple[str, str] | None]:
    match = _STATE_ABBREV_RE.search(taxpayer_address.upper())
    if not match:
        return None, None
    state = match.group(1)
    center_key = _STATE_TO_SERVICE_CENTER.get(state)
    if not center_key:
        return state, None
    return state, _SERVICE_CENTER_ADDRESSES[center_key]


def process_election_83b(
    order_id: str,
    intake_data: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    grant_date = _parse_date(str(intake_data["grant_date"]))
    filing_deadline = grant_date + timedelta(days=30)
    reference_day = today or date.today()

    taxpayer_name = str(intake_data["taxpayer_name"])
    taxpayer_address = str(intake_data["taxpayer_address"])
    company_name = str(intake_data["company_name"])
    property_description = str(intake_data["property_description"])
    share_count = int(intake_data["share_count"])
    fair_market_value = float(intake_data["fair_market_value_per_share"])
    exercise_price = float(intake_data["exercise_price_per_share"])
    vesting_schedule = str(intake_data["vesting_schedule"])

    grant_in_future = grant_date > reference_day
    deadline_passed = filing_deadline < reference_day
    days_past_deadline = (reference_day - filing_deadline).days if deadline_passed else 0

    if grant_in_future:
        summary = (
            f"The grant date you entered ({grant_date.isoformat()}) is in the future. "
            f"Confirm the grant date with your employer before mailing anything — an 83(b) election can only be filed for a grant that has actually occurred."
        )
        verdict = "block"
    elif deadline_passed:
        summary = (
            f"URGENT: the 30-day deadline for this 83(b) election has already passed. "
            f"The grant date was {grant_date.isoformat()} and the deadline was {filing_deadline.isoformat()} "
            f"({days_past_deadline} day{'s' if days_past_deadline != 1 else ''} ago). "
            f"A late 83(b) election is generally invalid and cannot be cured, but speak with a tax advisor before filing anything."
        )
        verdict = "block"
    else:
        days_remaining = (filing_deadline - reference_day).days
        summary = (
            f"Your 83(b) election packet is ready. Based on a grant date of {grant_date.isoformat()}, "
            f"the election must be mailed no later than {filing_deadline.isoformat()} "
            f"({days_remaining} day{'s' if days_remaining != 1 else ''} from today)."
        )
        verdict = "pass"

    if deadline_passed or grant_in_future:
        next_steps = [
            "Do not mail this packet before speaking with a tax advisor.",
            "Bring the grant documents, vesting schedule, and this summary to the advisor.",
            "If an 83(b) election is no longer viable, ask the advisor about alternatives — e.g., Section 83(i) (which can defer tax on qualified employer stock for up to 5 years if the company and grant qualify).",
        ]
    else:
        taxable_spread = max((fair_market_value - exercise_price) * share_count, 0.0)
        spread_line = (
            f"Your taxable spread at grant is ${taxable_spread:,.2f} (FMV minus amount paid, per share, times shares). "
            f"This is the amount you'd include in income now under the 83(b) election."
        )
        next_steps = [
            "Print the election letter and cover sheet.",
            "Sign the election letter before mailing it.",
            "Use USPS Certified Mail or an equivalent tracked service so you can prove the mailing date.",
            f"Deliver a signed copy of the election to the company ({company_name}) — this is required by Treas. Reg. §1.83-2(d).",
            "Keep a complete signed copy for your records and your tax preparer.",
            spread_line,
        ]

    state, service_center = _infer_service_center(taxpayer_address)

    election_lines = [
        taxpayer_name,
        taxpayer_address,
        "",
        "Election Under Section 83(b)",
        "",
        f"I hereby elect under Section 83(b) of the Internal Revenue Code with respect to {property_description} issued by {company_name}.",
        f"Grant date: {grant_date.isoformat()}",
        f"Shares: {share_count}",
        f"Fair market value per share at transfer: ${fair_market_value:0.4f}",
        f"Amount paid per share: ${exercise_price:0.4f}",
        f"Vesting schedule: {vesting_schedule}",
        "",
        "A copy of this statement should be retained with the taxpayer's records.",
    ]

    cover_lines = [
        "Mailing checklist",
        "",
        summary,
        "",
        "Checklist",
        *[f"- {step}" for step in next_steps],
    ]

    if service_center:
        cover_lines.extend([
            "",
            f"IRS service center (based on your address in {state})",
            service_center[0],
            service_center[1],
            "This is the address the IRS publishes for individual paper returns filed from your state.",
            "Confirm the current address on irs.gov/filing before mailing — the IRS updates these periodically.",
        ])
    else:
        cover_lines.extend([
            "",
            "IRS service center",
            "Guardian could not infer your IRS service center from the address you entered.",
            "Look up the correct center at irs.gov/filing/where-to-file-paper-tax-returns before mailing.",
        ])

    artifacts_dir = ELECTION_83B_DIR / order_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    # For blocked verdicts we still produce a PDF (so an advisor or user
    # reviewing the file has the grant details in one place), but we label
    # it as FOR REVIEW ONLY and omit the mailing cover sheet so the user
    # can't mistake it for a ready-to-send packet.
    if verdict == "block":
        review_lines = [
            "*** FOR ADVISOR REVIEW ONLY — DO NOT MAIL ***",
            "",
            summary,
            "",
        ] + election_lines
        review_path = artifacts_dir / "83b-advisor-review.pdf"
        review_path.write_bytes(build_text_pdf("83(b) Advisor Review Packet", review_lines))
        artifacts = [
            {
                "label": "Download advisor review packet (do not mail)",
                "filename": review_path.name,
                "path": str(review_path),
            }
        ]
    else:
        election_path = artifacts_dir / "83b-election-letter.pdf"
        cover_path = artifacts_dir / "83b-cover-sheet.pdf"
        election_path.write_bytes(build_text_pdf("83(b) Election Letter", election_lines))
        cover_path.write_bytes(build_text_pdf("83(b) Election Mailing Cover Sheet", cover_lines))
        artifacts = [
            {
                "label": "Download 83(b) election letter",
                "filename": election_path.name,
                "path": str(election_path),
            },
            {
                "label": "Download 83(b) cover sheet",
                "filename": cover_path.name,
                "path": str(cover_path),
            },
        ]

    if verdict == "block" and deadline_passed:
        mailing_headline = f"Deadline passed {days_past_deadline} day{'s' if days_past_deadline != 1 else ''} ago"
        mailing_summary = "Do not mail this packet without an advisor reviewing whether a late 83(b) election has any remaining path."
    elif verdict == "block" and grant_in_future:
        mailing_headline = "Confirm the grant date first"
        mailing_summary = "The grant date you entered is in the future. Do not mail anything until the grant has actually occurred."
    else:
        mailing_headline = "Mail your 83(b) election with proof"
        if service_center:
            addr_line = ", ".join(service_center)
            mailing_summary = (
                f"The IRS must receive evidence that the election was mailed within 30 days of the grant date. "
                f"Based on your {state} address, mail to {addr_line}. Confirm on irs.gov before mailing."
            )
        else:
            mailing_summary = (
                "The IRS must receive evidence that the election was mailed within 30 days of the grant date. "
                "Look up the correct IRS service center for your state on irs.gov/filing/where-to-file-paper-tax-returns before mailing."
            )

    return {
        "summary": summary,
        "verdict": verdict,
        "deadline_passed": deadline_passed,
        "days_past_deadline": days_past_deadline if deadline_passed else 0,
        "grant_in_future": grant_in_future,
        "filing_deadline": filing_deadline.isoformat(),
        "next_steps": next_steps,
        "mailing_instructions": {
            "headline": mailing_headline,
            "summary": mailing_summary,
            "steps": next_steps,
        },
        "artifacts": artifacts,
    }
