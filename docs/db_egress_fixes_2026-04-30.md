# DB egress fixes — 2026-04-30

After hitting Neon's free-tier data-transfer cap mid-dogfood, this is
the set of patches that addressed the root cause. All work is local
(no prod deploy yet, since prod DB is still rate-limited until quota
resets).

## Measured impact

Same eval-local user, 43 documents, 3 calls each:

| Endpoint | Before | After | Reduction |
|----------|--------|-------|-----------|
| `GET /api/dashboard/timeline` | 184 queries | 30 queries | **6.1×** |
| `GET /api/dashboard/documents?limit=50` | (not measured before) | 4 queries | — |

Numbers are query *count*; the byte savings on `defer(DocumentRow.ocr_text)`
are not separately measurable because both psycopg and SQLite report
`-1` rowcount on SELECTs at `after_cursor_execute` time, but the
ocr_text column being skipped is a per-row size win that compounds
linearly with doc count. For cl4183 prod (~184 docs) the projected
reduction is far larger because many of those queries were the N+1
ones that lazy-loaded `extracted_fields` per doc.

## Files changed

### `compliance_os/web/services/query_helpers.py` (new)
- `documents_loader_options()` — returns `(defer(ocr_text), selectinload(extracted_fields))`
- `light_user_checks_query(db, user_id)` — standard CheckRow query with the documents+extracted_fields chain eager-loaded

### `compliance_os/web/services/timeline_builder.py`
- `build_timeline()` and `build_stats()` switched from
  `db.query(CheckRow).filter(...).all()` to `light_user_checks_query(db, user_id).all()`
- Final return now caps `events` at `TIMELINE_EVENT_CAP=100` (most recent
  by date) and `documents` at `TIMELINE_DOC_CAP=50` (newest first)
- Added `events_total` and `documents_total` to the response so the UI
  can render "showing 100 of 187" if it wants

### `compliance_os/web/routers/dashboard.py`
- All three `db.query(CheckRow)...all()` callsites switched to `light_user_checks_query`
- `GET /api/dashboard/documents` now honors `?limit=N&offset=M` (default 50, max 500)

### `compliance_os/web/routers/chat.py`
- Both `db.query(CheckRow)...all()` callsites switched to `light_user_checks_query`

### `compliance_os/web/services/dashboard_marketplace.py`
- The single `db.query(CheckRow)...all()` callsite switched

### `compliance_os/web/middleware/db_egress.py` (new)
- SQLAlchemy `after_cursor_execute` listener counts queries + rows per request
- FastAPI middleware logs `db.egress route=... queries=N rows=M ms=...` at
  request end
- Uses a `ContextVar` holding a *mutable dict* so the listener (running
  in FastAPI's threadpool worker) can mutate counters that the middleware
  (in the request task) reads after `await call_next(...)`. ContextVar
  reassignment doesn't propagate across that boundary; mutation does.
- Setting `DB_EGRESS_HEADERS=on` adds `X-DB-Queries` / `X-DB-Rows` /
  `X-DB-Est-Bytes` response headers for browser-tab visibility.
- Off via `DB_EGRESS_LOGGING=off`.

### `compliance_os/web/app.py`
- Installs egress listener in `lifespan()`
- Registers `DBEgressMiddleware` before `CORSMiddleware`

## What this does NOT change

- The actual prod DB outage — Neon is still rate-limited until reset (likely May 1 UTC, monthly per Neon docs)
- The classifier gaps from the earlier eval (those are upstream of any DB chatter)
- The frontend contract — `/timeline` still returns the same keys; `events` and `documents` may now be capped but the new `events_total`/`documents_total` fields are additive

## Next steps

1. **Wait for Neon reset** (~hours, depending on their reset schedule) OR pay $19 for Launch as immediate insurance
2. **Deploy these patches** — should reduce per-request DB egress 5-10× steady-state on prod cl4183
3. **Watch the `db.egress` log lines** for any future regression — anything > ~50 queries on `/timeline` is new chattiness worth investigating
4. **Optional**: add a `since=<iso_date>` param to `/timeline` for users who want events older than the cap (not urgent — the cap was set deliberately generous)

## Verification commands

After deploy, smoke-test the same way:

```bash
TOKEN=$(...mint a JWT...)
curl -s -D /tmp/h.txt -o /dev/null -H "Authorization: Bearer $TOKEN" \
  "https://guardian-compliance.fly.dev/api/dashboard/timeline"
grep -i "x-db" /tmp/h.txt   # only with DB_EGRESS_HEADERS=on
flyctl logs -a guardian-compliance | grep "db.egress"
```
