"""FBAR compliance check service."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from compliance_os.web.models.database import DATA_DIR
from compliance_os.web.services.pdf_builder import build_text_pdf


FBAR_CHECK_DIR = DATA_DIR / "marketplace" / "fbar_check"


def _fbar_due_date(tax_year: int) -> date:
    return date(tax_year + 1, 10, 15)


def process_fbar_check(order_id: str, intake_data: dict[str, Any]) -> dict[str, Any]:
    accounts = intake_data.get("accounts") or []
    aggregate = int(sum(float(account.get("max_balance_usd") or 0) for account in accounts))
    tax_year = int(intake_data.get("tax_year") or date.today().year - 1)
    due_date = _fbar_due_date(tax_year)
    requires_fbar = aggregate > 10000

    if requires_fbar:
        summary = (
            f"FinCEN filing is required for tax year {tax_year}. "
            f"Your reported aggregate maximum balance was ${aggregate:,}, which is above the $10,000 threshold."
        )
        next_steps = [
            "Use the BSA E-Filing System to submit FinCEN Form 114 online.",
            "Review each foreign account one more time before filing to confirm the maximum balance and account numbers.",
            f"File by {due_date.isoformat()} and keep the confirmation page for your records.",
        ]
    else:
        summary = (
            f"Based on the accounts entered, your aggregate maximum balance for tax year {tax_year} was "
            f"${aggregate:,}, which does not trigger an FBAR filing requirement."
        )
        next_steps = [
            "Keep a record of the balances you used in case the account mix changes later.",
            "Re-check the aggregate maximum balance if you open new foreign accounts during the year.",
        ]

    packet_lines = [
        summary,
        "",
        "Accounts included",
    ]
    for account in accounts:
        packet_lines.append(
            f"- {account.get('institution_name')} ({account.get('country')}), "
            f"{account.get('account_type')}, last4 {account.get('account_number_last4')}, "
            f"max ${float(account.get('max_balance_usd') or 0):,.0f}"
        )

    packet_lines.extend(
        [
            "",
            "Next steps",
            *[f"- {step}" for step in next_steps],
        ]
    )

    artifacts_dir = FBAR_CHECK_DIR / order_id / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    packet_path = artifacts_dir / "fbar-draft-packet.pdf"
    packet_path.write_bytes(build_text_pdf("FBAR Compliance Check", packet_lines, subtitle=f"Tax year {tax_year}"))

    return {
        "summary": summary,
        "requires_fbar": requires_fbar,
        "aggregate_max_balance_usd": aggregate,
        "filing_deadline": due_date.isoformat(),
        "next_steps": next_steps,
        "accounts": accounts,
        "artifacts": [
            {
                "label": "Download FBAR draft packet",
                "filename": packet_path.name,
                "path": str(packet_path),
            }
        ],
    }
