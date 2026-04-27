"""Recover a professional-search row that got stuck in `running`.

When fly redeploys the machine mid-run, BackgroundTasks runners die
without updating the row. The personas may have finished and written
their YAMLs to /data/output/... but `firms_data`, `tier_report`,
`status=complete`, and `completed_at` never got set.

This script picks up from after the per-persona dispatch:
  1. Loads persona YAMLs already on disk (skip if any are missing)
  2. Runs aggregate_firms → row.firms_data
  3. Runs the tier comparison query → row.tier_report
  4. Sets status=complete + completed_at

Run on prod:
    fly ssh console -a guardian-compliance -C \\
        "python /app/scripts/recover_stuck_search.py <search_id>"
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: recover_stuck_search.py <search_id>", file=sys.stderr)
        return 1
    search_id = sys.argv[1]

    from compliance_os.professional_search.aggregator import (
        aggregate_firms,
        load_persona_yamls,
    )
    from compliance_os.professional_search.db import (
        attorney_comparison,
        connect_diligence,
        init_diligence_schema,
        ingest_docs,
        vendor_comparison,
    )
    from compliance_os.web.models.database import get_session
    from compliance_os.web.models.tables import ProfessionalSearchRequestRow

    db = next(get_session())
    try:
        row = (
            db.query(ProfessionalSearchRequestRow)
            .filter_by(id=search_id)
            .first()
        )
        if row is None:
            print(f"ERROR: search {search_id} not found", file=sys.stderr)
            return 1
        if row.status == "complete":
            print(f"already complete; nothing to do")
            return 0

        print(f"recovering {search_id} (status={row.status})")
        statuses = row.persona_status or {}
        yaml_paths = [
            s.get("output_path")
            for s in statuses.values()
            if s.get("status") == "complete" and s.get("output_path")
        ]
        if not yaml_paths:
            print("no completed personas — nothing to aggregate", file=sys.stderr)
            row.status = "failed"
            row.error = "All personas failed before deploy interrupted aggregation"
            row.completed_at = datetime.utcnow()
            db.commit()
            return 1
        # Verify the YAMLs actually exist on the volume — if /data was
        # ephemeral or the tmp-cleaned them, we can't recover.
        missing = [p for p in yaml_paths if not Path(p).exists()]
        if missing:
            print(f"missing YAMLs: {missing}", file=sys.stderr)
            row.status = "failed"
            row.error = f"YAMLs missing post-deploy: {missing[:3]}"
            row.completed_at = datetime.utcnow()
            db.commit()
            return 1

        init_diligence_schema()
        ingest_docs(yaml_paths)

        try:
            yamls = load_persona_yamls(row)
            aggregated = aggregate_firms(yamls)
            row.firms_data = aggregated
            db.commit()
            print(f"firms_data: {len(aggregated)} unique firms")
        except Exception as exc:
            db.rollback()
            print(f"firms_data persist failed: {exc}", file=sys.stderr)

        with connect_diligence() as dconn:
            if (
                row.vertical.startswith("immigration")
                or row.vertical.endswith("attorney")
                or row.vertical == "attorney"
            ):
                rows = attorney_comparison(dconn)
            else:
                vendor_type_map = {"cpa": "cpa", "bank": "bank", "caa": "caa"}
                vt = vendor_type_map.get(row.vertical, None)
                rows = vendor_comparison(dconn, vendor_type=vt)
        rows = [r for r in rows if r.get("purpose") == row.purpose]

        row.tier_report = rows
        row.status = "complete"
        row.completed_at = datetime.utcnow()
        db.commit()
        print(f"tier_report: {len(rows)} rows; status=complete")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
