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
    """Find and recover stuck `running` searches AND stuck `enriching`
    rows. No-op if nothing stuck.

    Two-headed because the search has two state machines that can each
    get killed by SIGTERM mid-run:
      * `status=running` — Stage 1 persona dispatch was interrupted; we
        re-aggregate from on-disk YAMLs.
      * `enrichment_status=enriching` — Stage 2 per-firm enrichment was
        interrupted; we re-dispatch the enrichment runner. Re-runs are
        idempotent (overwrites the underscore-prefixed enrichment keys).
    """
    db = next(get_session())
    try:
        cutoff = datetime.utcnow() - RECOVERY_GRACE
        candidates = (
            db.query(ProfessionalSearchRequestRow)
            .filter(ProfessionalSearchRequestRow.status == "running")
            .filter(ProfessionalSearchRequestRow.updated_at < cutoff)
            .all()
        )
        if candidates:
            logger.info("search reaper: %d stuck running rows", len(candidates))
            for row in candidates:
                _recover_one(row, db)

        # Stage 2 stuck rows: enrichment_started_at set, status=enriching,
        # but the runner died before flipping to complete. Re-dispatch.
        stuck_enriching = (
            db.query(ProfessionalSearchRequestRow)
            .filter(ProfessionalSearchRequestRow.enrichment_status == "enriching")
            .filter(ProfessionalSearchRequestRow.enrichment_started_at < cutoff)
            .all()
        )
        if stuck_enriching:
            logger.info(
                "search reaper: %d stuck enriching rows", len(stuck_enriching),
            )
            for row in stuck_enriching:
                _recover_stuck_enrichment(row, db)
    finally:
        db.close()


def _recover_stuck_enrichment(row: ProfessionalSearchRequestRow, db) -> None:
    """Re-dispatch enrichment for a row that was killed mid-flight.

    Hard cap: after 1 hour of being stuck, give up and mark `failed`.
    The user sees a "Re-enrich (free)" button on the /paid page that
    re-triggers via the same code path.
    """
    age = datetime.utcnow() - (row.enrichment_started_at or datetime.utcnow())
    if age > timedelta(hours=1):
        row.enrichment_status = "failed"
        row.enrichment_error = (
            f"Enrichment stuck > {age.total_seconds() / 60:.0f}min "
            "(likely repeated deploy interrupts); user can re-trigger via "
            "the /paid page CTA."
        )
        row.enrichment_completed_at = datetime.utcnow()
        try:
            db.commit()
            logger.warning("reaper: enrichment %s gave up after %s", row.id, age)
        except Exception:
            db.rollback()
            logger.exception("reaper: failed to mark stuck enrichment as failed")
        return

    # Within the recovery window — re-dispatch synchronously (we're
    # in the boot path, no event loop yet). The enrichment runner is
    # synchronous at the entrypoint and uses `asyncio.run` internally.
    try:
        from compliance_os.web.services.enrichment_runner import run_enrichment_sync
        # Fire-and-forget via thread so app boot isn't blocked. The
        # runner has its own DB session, so we can release the boot-time
        # session immediately after spawning.
        import threading
        threading.Thread(
            target=run_enrichment_sync,
            args=(row.id,),
            daemon=True,
            name=f"enrichment-recovery-{row.id[:8]}",
        ).start()
        logger.info("reaper: re-dispatched enrichment for %s", row.id)
    except Exception:
        logger.exception("reaper: failed to re-dispatch enrichment for %s", row.id)


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
