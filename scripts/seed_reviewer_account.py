"""Seed a reviewer account for the Anthropic Connector Directory submission.

Usage:
    # Local dev DB:
    conda run -n compliance-os python scripts/seed_reviewer_account.py

    # On fly (prod):
    fly ssh console -a guardian-compliance -C \
        "python /app/scripts/seed_reviewer_account.py --prod"

Creates a user at connector-reviewer@guardian.demo with a pre-issued
OpenClaw API token, and seeds a handful of findings + a deadline so
the reviewer sees non-empty dashboard / MCP responses on first use.
Prints the email, password, and token to stdout — capture these for
the submission form.
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compliance_os.web.models.auth import UserRow
from compliance_os.web.models.database import get_engine, get_session
from compliance_os.web.models.tables_v2 import CheckRow, FindingRow
from compliance_os.web.services.auth_service import hash_password, issue_openclaw_token


REVIEWER_EMAIL = "connector-reviewer@guardian.demo"


def _random_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Rv-" + "".join(secrets.choice(alphabet) for _ in range(16))


def _seed_findings(db, user_id: str) -> None:
    """Seed one Check with three findings of varied severity."""
    check = CheckRow(
        user_id=user_id,
        track="reviewer_seed",
        stage="completed",
        status="completed",
    )
    db.add(check)
    db.flush()

    seeds = [
        ("critical", "immigration", "I-983 training plan missing",
         "Add a signed I-983 before STEM OPT employment begins.",
         "Unauthorized employment risk if work starts without I-983 on file."),
        ("warning", "immigration", "Passport expires within 6 months of H-1B filing",
         "Renew passport now; file H-1B with renewal receipt as supplement.",
         "USCIS may flag for additional evidence."),
        ("info", "tax", "Form 8843 standalone — not filed yet",
         "Generate and mail by April 15.",
         "Filing obligation for F-1 even with no US income."),
    ]
    for sev, cat, title, action, conseq in seeds:
        db.add(FindingRow(
            check_id=check.id,
            rule_id=f"seed_{sev}",
            severity=sev,
            category=cat,
            title=title,
            action=action,
            consequence=conseq,
            immigration_impact=(cat == "immigration"),
        ))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rotate", action="store_true",
                   help="Rotate password + token even if account exists")
    args = p.parse_args()

    get_engine()  # ensure schema exists
    session_gen = get_session()
    db = next(session_gen)

    try:
        user = db.query(UserRow).filter(UserRow.email == REVIEWER_EMAIL).first()
        password = _random_password()

        if user is None:
            user = UserRow(
                email=REVIEWER_EMAIL,
                password_hash=hash_password(password),
                role="user",
            )
            db.add(user)
            db.flush()
            created = True
        else:
            created = False
            if args.rotate:
                user.password_hash = hash_password(password)
                db.flush()
            else:
                password = "(unchanged — re-run with --rotate to reset)"

        token_row, token = issue_openclaw_token(user, db)

        # Seed findings only on create (don't pile up re-runs)
        if created:
            _seed_findings(db, user.id)

        db.commit()

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print()
        print("=" * 62)
        print("  Reviewer account seeded")
        print("=" * 62)
        print(f"  email:    {REVIEWER_EMAIL}")
        print(f"  password: {password}")
        print(f"  token:    {token}")
        print(f"  created:  {'yes' if created else 'no (pre-existing)'}")
        print(f"  when:     {now}")
        print(f"  findings: 3 seeded ({'yes' if created else 'already present'})")
        print("=" * 62)
        print()
        print("  Paste password + token into the Anthropic submission")
        print("  form's 'Test account credentials' field. Revoke the")
        print("  token later via /connect -> Rotate token.")
        print()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
