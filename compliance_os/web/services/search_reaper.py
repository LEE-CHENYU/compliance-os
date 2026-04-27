"""Boot-time recovery for professional-search rows stuck in `running`.

Called from FastAPI lifespan startup. Finds any row where
`status == "running"` AND every entry in `persona_status` is `complete`
or `failed` (i.e., dispatch is done) AND `tier_report` is empty. Runs
the same post-persona aggregation that the live runner would have run,
or fails the row if recovery isn't possible (missing YAMLs, etc.).

Triggered on every app boot so a redeploy SIGTERM mid-run can't leave
rows orphaned past the next restart. Safe to run repeatedly: idempotent
in the success case, makes a single pass per boot in the failure case.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from compliance_os.web.models.database import get_session
from compliance_os.web.models.tables import ProfessionalSearchRequestRow

logger = logging.getLogger(__name__)

# Don't try to recover rows newer than this — give the live runner time
# to finish on the current machine before we step in. 10 minutes covers
# the typical persona dispatch (5-7m on the slowest persona) plus margin.
RECOVERY_GRACE = timedelta(minutes=10)


def reap_stuck_searches() -> None:
    """Find and recover stuck `running` searches. No-op if nothing stuck."""
    db = next(get_session())
    try:
        cutoff = datetime.utcnow() - RECOVERY_GRACE
        candidates = (
            db.query(ProfessionalSearchRequestRow)
            .filter(ProfessionalSearchRequestRow.status == "running")
            .filter(ProfessionalSearchRequestRow.updated_at < cutoff)
            .all()
        )
        if not candidates:
            return
        logger.info("search reaper: %d stuck rows to inspect", len(candidates))
        for row in candidates:
            _recover_one(row, db)
    finally:
        db.close()


def _recover_one(row: ProfessionalSearchRequestRow, db) -> None:
    statuses = row.persona_status or {}
    if not statuses:
        # Hadn't even dispatched personas — fail it; user can retry.
        _fail(row, db, "Stuck before persona dispatch (likely deploy interrupt)")
        return

    # If any persona is still running, the live runner may yet finish.
    # Skip — we'll get it on the next boot if it's still stuck.
    if any(s.get("status") == "running" for s in statuses.values()):
        return

    yaml_paths = [
        s.get("output_path")
        for s in statuses.values()
        if s.get("status") == "complete" and s.get("output_path")
    ]
    if not yaml_paths:
        _fail(row, db, "All personas failed; nothing to aggregate")
        return

    missing = [p for p in yaml_paths if not Path(p).exists()]
    if missing:
        _fail(row, db, f"Persona YAMLs missing: {missing[:3]}")
        return

    try:
        # Imports are inside the function so a missing aggregator package
        # at boot doesn't crash the reaper. Names mirror the live runner
        # (professional_search_runner.py) — `connect`/`init_schema` are
        # aliased to the more descriptive *_diligence names, and
        # ingest_docs lives in `ingest.py`, not `db.py`.
        from compliance_os.professional_search.aggregator import (
            aggregate_firms,
            load_persona_yamls,
        )
        from compliance_os.professional_search.db import (
            attorney_comparison,
            vendor_comparison,
            connect as connect_diligence,
            init_schema as init_diligence_schema,
        )
        from compliance_os.professional_search.ingest import ingest_docs

        init_diligence_schema()
        ingest_docs(yaml_paths)

        try:
            yamls = load_persona_yamls(row)
            aggregated = aggregate_firms(yamls)
            row.firms_data = aggregated
            db.commit()
            logger.info(
                "reaper: %s firms_data persisted (%d firms)",
                row.id, len(aggregated),
            )
        except Exception:
            db.rollback()
            logger.exception("reaper: firms_data persist failed for %s", row.id)

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
        logger.info(
            "reaper: %s recovered (status=complete, %d tier_report rows)",
            row.id, len(rows),
        )
    except Exception as exc:
        db.rollback()
        logger.exception("reaper: recovery failed for %s", row.id)
        _fail(row, db, f"Recovery error: {type(exc).__name__}: {exc}")


def _fail(row: ProfessionalSearchRequestRow, db, reason: str) -> None:
    """Mark a row failed with a short reason. Last resort when recovery
    isn't possible — exposes the row to the user with an explainable error
    instead of an indefinite `running` spinner."""
    row.status = "failed"
    row.error = reason[:500]
    row.completed_at = datetime.utcnow()
    try:
        db.commit()
        logger.warning("reaper: failed %s — %s", row.id, reason)
    except Exception:
        db.rollback()
        logger.exception("reaper: even failure-mark failed for %s", row.id)
