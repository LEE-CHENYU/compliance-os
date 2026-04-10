"""83(b) election packet generation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.services.pdf_builder import build_text_pdf


ELECTION_83B_DIR = DATA_DIR / "marketplace" / "election_83b"


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def process_election_83b(order_id: str, intake_data: dict[str, Any]) -> dict[str, Any]:
    grant_date = _parse_date(str(intake_data["grant_date"]))
    filing_deadline = grant_date + timedelta(days=30)

    taxpayer_name = str(intake_data["taxpayer_name"])
    taxpayer_address = str(intake_data["taxpayer_address"])
    company_name = str(intake_data["company_name"])
    property_description = str(intake_data["property_description"])
    share_count = int(intake_data["share_count"])
    fair_market_value = float(intake_data["fair_market_value_per_share"])
    exercise_price = float(intake_data["exercise_price_per_share"])
    vesting_schedule = str(intake_data["vesting_schedule"])

    summary = (
        f"Your 83(b) election packet is ready. Based on a grant date of {grant_date.isoformat()}, "
        f"the election must be mailed no later than {filing_deadline.isoformat()}."
    )
    next_steps = [
        "Print the election letter and cover sheet.",
        "Sign the election letter before mailing it.",
        "Use USPS Certified Mail or an equivalent tracked service so you can prove the mailing date.",
        "Keep a complete signed copy for your records and your tax preparer.",
    ]

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
        "",
        "Important",
        "- Guardian does not yet infer your exact IRS service center address for 83(b) elections.",
        "- Confirm the IRS address that corresponds to the federal return you will file.",
    ]

    artifacts_dir = ELECTION_83B_DIR / order_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    election_path = artifacts_dir / "83b-election-letter.pdf"
    cover_path = artifacts_dir / "83b-cover-sheet.pdf"
    election_path.write_bytes(build_text_pdf("83(b) Election Letter", election_lines))
    cover_path.write_bytes(build_text_pdf("83(b) Election Mailing Cover Sheet", cover_lines))

    return {
        "summary": summary,
        "filing_deadline": filing_deadline.isoformat(),
        "next_steps": next_steps,
        "mailing_instructions": {
            "headline": "Mail your 83(b) election with proof",
            "summary": "The IRS must receive evidence that the election was mailed within 30 days of the grant date.",
            "steps": next_steps,
        },
        "artifacts": [
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
        ],
    }
