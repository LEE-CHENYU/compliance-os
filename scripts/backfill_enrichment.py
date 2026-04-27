"""One-shot backfill: run Stage 2 enrichment over already-paid searches.

After deploying the click-triggered Stage 2 flow, the existing paid +
complete searches in prod still have firms_data with only Stage 1
firm-level credentials — no individual attorney band, no verified
sources, no alternate-attorney suggestions. Their `enrichment_status`
defaults to `idle`.

This script picks them up one-at-a-time (sequential, not parallel) and
runs the same enrichment runner the live click trigger would. Skip
already-enriched and unpaid rows.

Run on prod via:
    fly ssh console -a guardian-compliance -C "python /app/scripts/backfill_enrichment.py"

Optional flags:
    --dry-run     just list what would be enriched
    --search-id X enrich a specific row only
    --limit N     stop after N rows (cost control)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="List rows that would be enriched, don't run")
    p.add_argument("--search-id", default=None,
                   help="Enrich only this search (otherwise all eligible)")
    p.add_argument("--limit", type=int, default=None,
                   help="Stop after this many rows")
    args = p.parse_args()

    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.tables import ProfessionalSearchRequestRow
    from compliance_os.web.services.enrichment_runner import run_enrichment_sync

    db = next(get_session())
    try:
        q = db.query(ProfessionalSearchRequestRow)
        if args.search_id:
            q = q.filter(ProfessionalSearchRequestRow.id == args.search_id)
        else:
            # Eligible: paid + complete + has firms_data + enrichment idle
            q = (
                q.filter(ProfessionalSearchRequestRow.paid_at.isnot(None))
                .filter(ProfessionalSearchRequestRow.status == "complete")
                .filter(
                    (ProfessionalSearchRequestRow.enrichment_status == "idle")
                    | (ProfessionalSearchRequestRow.enrichment_status == "failed")
                )
                .filter(ProfessionalSearchRequestRow.firms_data.isnot(None))
            )

        rows = q.order_by(ProfessionalSearchRequestRow.created_at.desc()).all()
        print(f"found {len(rows)} eligible row(s)")
        for r in rows:
            firms = r.firms_data or []
            print(
                f"  {r.id}  vertical={r.vertical:25s}  firms={len(firms):2d}  "
                f"paid_at={r.paid_at}  enrichment={r.enrichment_status}"
            )

        if args.dry_run:
            return 0

        if args.limit:
            rows = rows[: args.limit]
            print(f"limit={args.limit}; enriching first {len(rows)}")

        for i, r in enumerate(rows, start=1):
            print(f"\n[{i}/{len(rows)}] enriching {r.id}…")
            t0 = time.time()
            try:
                run_enrichment_sync(r.id)
            except Exception as exc:
                print(f"  ERROR: {type(exc).__name__}: {exc}")
                continue
            elapsed = time.time() - t0
            db.refresh(r)
            print(
                f"  done in {elapsed:.1f}s  status={r.enrichment_status}  "
                f"err={r.enrichment_error}"
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
