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
    missing_balance_accounts = [
        a for a in accounts if a.get("max_balance_usd") in (None, "")
    ]
    aggregate = round(sum(float(account.get("max_balance_usd") or 0) for account in accounts), 2)
    tax_year = int(intake_data.get("tax_year") or date.today().year - 1)
    due_date = _fbar_due_date(tax_year)
    requires_fbar = aggregate > 10000

    # Warn if any account is missing its max balance — the aggregate may be
    # understated, which could flip the filing determination from "not required"
    # to "required."
    missing_balance_warning: str | None = None
    if missing_balance_accounts:
        missing_names = [
            str(a.get("institution_name") or f"Account #{i + 1}")
            for i, a in enumerate(accounts) if a.get("max_balance_usd") in (None, "")
        ]
        missing_balance_warning = (
            f"WARNING: {len(missing_balance_accounts)} account(s) have no max balance entered "
            f"({', '.join(missing_names)}). Their balance was treated as $0 in the aggregate. "
            f"If these accounts held any value, the actual aggregate may be higher — verify before relying on this result."
        )

    if requires_fbar:
        # Form 8938 (FATCA) thresholds are higher than FBAR but vary by filing
        # status and residence:
        #   Single/MFS in US: $50K end-of-year OR $75K at any time
        #   MFJ in US:        $100K end-of-year OR $150K at any time
        #   Single abroad:    $200K end-of-year OR $300K at any time
        #   MFJ abroad:       $400K end-of-year OR $600K at any time
        # If aggregate exceeds the lowest threshold ($50K), Form 8938 is likely
        # also triggered — flag explicitly rather than just disambiguate.
        also_likely_8938 = aggregate > 50000
        summary = (
            f"FinCEN filing is required for tax year {tax_year}. "
            f"Your reported aggregate maximum balance was ${aggregate:,.2f}, which is above the $10,000 threshold."
        )
        if also_likely_8938:
            summary += (
                f" At ${aggregate:,.2f} you also likely meet Form 8938 (FATCA) thresholds — both filings may be required."
            )
        next_steps = [
            "Use the BSA E-Filing System (bsaefiling.fincen.treas.gov) to submit FinCEN Form 114 online.",
            "List every foreign account, not just those individually over $10,000 — the threshold is on the aggregate maximum balance.",
            "Convert foreign-currency balances to USD using the Treasury Reporting Rates of Exchange for the last day of the year (fiscal.treasury.gov/reports-statements/treasury-reporting-rates-exchange).",
            "Review each account's maximum balance and account number before filing.",
            f"File by {due_date.isoformat()} (automatic extension from April 15) and keep the BSA confirmation page.",
            "Non-filing penalties can reach ~$16K/year (non-willful) or the greater of ~$129K or 50% of balance (willful).",
            "On your Form 1040, also check the Schedule B Part III box for foreign accounts (line 7a) — failure to do so is a separate notice trigger.",
        ]
        if also_likely_8938:
            next_steps.extend([
                f"At ${aggregate:,.2f} aggregate, you likely also need Form 8938 (FATCA) attached to your Form 1040. Thresholds: single US filer $50K end-of-year or $75K any time; MFJ US $100K/$150K; abroad $200K/$300K (single) or $400K/$600K (MFJ). Confirm your filing-status threshold.",
                "FBAR and Form 8938 cover overlapping but not identical accounts — both may need to be filed independently. Form 8938 penalties: $10K initial + $10K/30 days continuing (max $50K). Reasonable-cause exception requires written explanation.",
            ])
        else:
            next_steps.append(
                "FBAR (FinCEN 114) is filed with FinCEN, not the IRS. It is separate from FATCA Form 8938, which has a higher threshold and is attached to the 1040 return.",
            )
    else:
        summary = (
            f"Based on the accounts entered, your aggregate maximum balance for tax year {tax_year} was "
            f"${aggregate:,.2f}, which is below the $10,000 threshold — no FBAR filing is required."
        )
        next_steps = [
            "No filing action needed for this tax year based on the balances you entered.",
            "Keep a record of the balances you used in case the account mix changes later.",
            "Re-check the aggregate maximum balance if you open new foreign accounts or receive deposits during the year.",
            "FBAR (FinCEN 114) is separate from FATCA Form 8938, which has a higher threshold and different filing channel.",
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

    if requires_fbar:
        packet_path = artifacts_dir / "fbar-draft-packet.pdf"
        packet_path.write_bytes(build_text_pdf("FBAR Compliance Check", packet_lines, subtitle=f"Tax year {tax_year}"))
        artifacts = [{"label": "Download FBAR draft packet", "filename": packet_path.name, "path": str(packet_path)}]
    else:
        # No filing required → don't generate a "draft packet" that contradicts
        # the no-filing conclusion. Produce a short summary instead.
        summary_path = artifacts_dir / "fbar-review-summary.pdf"
        summary_path.write_bytes(build_text_pdf(
            "FBAR Review Summary — no filing required",
            packet_lines,
            subtitle=f"Tax year {tax_year}",
        ))
        artifacts = [{"label": "Download FBAR review summary", "filename": summary_path.name, "path": str(summary_path)}]

    if missing_balance_warning:
        summary += f" {missing_balance_warning}"
        next_steps.insert(0, missing_balance_warning)

    return {
        "summary": summary,
        "requires_fbar": requires_fbar,
        "missing_balance_accounts": len(missing_balance_accounts),
        "aggregate_max_balance_usd": aggregate,
        # Only expose a filing deadline when a filing is actually required.
        "filing_deadline": due_date.isoformat() if requires_fbar else None,
        "next_steps": next_steps,
        "accounts": accounts,
        "artifacts": artifacts,
    }
