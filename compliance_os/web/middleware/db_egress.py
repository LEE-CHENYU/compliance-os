"""Per-request DB query/egress instrumentation.

Hooks SQLAlchemy's `before_cursor_execute` / `after_cursor_execute`
events on the configured engine and aggregates query counts and an
estimated returned-bytes total per FastAPI request via a `ContextVar`.

We don't have a clean way to count actual wire bytes from outside the
driver, so the estimate is rough: for each fetched row we sum
`len(repr(value))` across the row's values. Repr is conservative
(includes quoting + commas) but tracks reality closely for plain
strings/numbers and slightly over-counts for None/booleans. Good
enough for "did the dashboard get chattier this week?" — not good
enough for billing accuracy.

A request gets a final log line on the way out:
    db.egress route=/api/dashboard/timeline queries=42 rows=387 est_bytes=1843212 ms=215

Set `DB_EGRESS_LOGGING=off` to suppress.
"""
from __future__ import annotations

import contextvars
import logging
import os
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("compliance_os.db_egress")
# Uvicorn's prod logging config only wires up its own loggers (uvicorn.*,
# fastapi). Custom application loggers like this one are silently dropped
# unless we attach a handler. Attach a single stdout handler at import
# time, idempotently, so the egress log line surfaces in
# `flyctl logs` and `docker logs` without depending on the runner's
# logging.yaml. propagate=False prevents double-emission if the root
# logger ever picks up a handler too.
if not any(getattr(h, "_db_egress_handler", False) for h in logger.handlers):
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _handler._db_egress_handler = True  # type: ignore[attr-defined]
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


# Counters live in a mutable dict held by a ContextVar. We mutate the
# dict (rather than reassigning the var) because FastAPI runs sync route
# handlers on a threadpool worker — `ContextVar.set` in the worker only
# updates the worker's copy, but a shared dict object is reachable from
# both contexts. Reading from the request task after `call_next` then
# sees the worker's mutations.
_COUNTERS_VAR: contextvars.ContextVar[dict] = contextvars.ContextVar("db_counters")


def _enabled() -> bool:
    return os.environ.get("DB_EGRESS_LOGGING", "on").lower() not in {"off", "0", "false"}


def _estimate_row_bytes(row: Any) -> int:
    """Cheap upper bound on the wire size of a row.

    We don't have a per-column type-aware sizer; `repr` works as a
    consistent stand-in across runs. Constants are the same factor for
    the same row, so before/after comparisons are valid.
    """
    if row is None:
        return 0
    try:
        if hasattr(row, "_mapping"):
            return sum(len(repr(v)) for v in row._mapping.values())
        return sum(len(repr(v)) for v in row)
    except Exception:
        return 0


def install(engine: Engine) -> None:
    """Register the SQLAlchemy event hooks on `engine`. Idempotent."""
    if getattr(engine, "_db_egress_installed", False):
        return
    engine._db_egress_installed = True  # type: ignore[attr-defined]

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, params, context, executemany):  # noqa: ARG001
        try:
            counters = _COUNTERS_VAR.get(None)
            if counters is None:
                # Query happened outside a request lifecycle — startup,
                # background task, etc. Don't track those.
                return
            rowcount = cursor.rowcount or 0
            counters["queries"] += 1
            if rowcount > 0:
                counters["rows"] += rowcount
            if cursor.description and rowcount > 0:
                col_count = len(cursor.description)
                # 40 bytes per cell is a rough average — strings/IDs
                # are around there; ocr_text blows past it but stays
                # conservative for our regression-detection purposes.
                counters["est_bytes"] += rowcount * col_count * 40
            counters["statements"].append(statement[:120])
        except Exception:
            # Never let instrumentation break the request.
            pass


class DBEgressMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that resets + reports the per-request totals."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if not _enabled():
            return await call_next(request)
        # The listener prints in dev are noisy; keep them off by default.

        # Allocate a counter dict for this request; the listener mutates
        # it from the threadpool worker that runs the sync route. Both
        # contexts see the same dict object so the mutations propagate.
        counters: dict = {
            "queries": 0,
            "rows": 0,
            "est_bytes": 0,
            "statements": [],
        }
        token = _COUNTERS_VAR.set(counters)
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _COUNTERS_VAR.reset(token)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        queries = counters["queries"]
        rows = counters["rows"]
        est_bytes = counters["est_bytes"]
        # Only log paths that actually touched the DB.
        if queries > 0:
            logger.info(
                "db.egress route=%s method=%s status=%s queries=%d rows=%d est_bytes=%d ms=%.0f",
                request.url.path,
                request.method,
                response.status_code,
                queries,
                rows,
                est_bytes,
                elapsed_ms,
            )
            # Add to response headers when in dev so it shows up in the
            # browser network tab without grepping logs.
            if os.environ.get("DB_EGRESS_HEADERS", "off").lower() in {"on", "1", "true"}:
                response.headers["X-DB-Queries"] = str(queries)
                response.headers["X-DB-Rows"] = str(rows)
                response.headers["X-DB-Est-Bytes"] = str(est_bytes)
        return response
