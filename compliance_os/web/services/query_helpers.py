"""Shared loader options for the high-traffic dashboard reads.

The dashboard timeline, stats, chat, and marketplace endpoints each pull
all of a user's checks and the documents under them. Without explicit
loader options the ORM does two expensive things on every call:

1. Lazy-loads `DocumentRow.extracted_fields` per document (N+1).
2. Selects every column on `DocumentRow`, including `ocr_text` (Text).

Both are wasteful across the wire. `selectinload` collapses the N+1
into a single IN-list query; `defer` keeps the heavy text columns out
of the wire payload until something actually reads them.

These helpers exist to make the right defaults the easy defaults — any
code path that needs `extracted_fields` should funnel through
`light_user_checks_query` rather than rolling a bare `db.query(CheckRow)`.
"""
from __future__ import annotations

from sqlalchemy.orm import Query, Session, defer, selectinload

from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow


import os as _os
_BENCHMARK_DISABLE = _os.environ.get("QUERY_HELPERS_DISABLE", "").lower() in {"1", "true", "on"}


def documents_loader_options() -> tuple:
    """Loader options for reading DocumentRow rows in dashboard contexts.

    Skips `ocr_text` (the OCR'd full-page text — can be 10-100KB per doc
    and is not used by any timeline / stats / chat aggregator) while
    eagerly fetching `extracted_fields` to kill the N+1.

    Use as `query.options(*documents_loader_options())`.
    """
    if _BENCHMARK_DISABLE:
        return ()  # noqa: RET505 — measurement-mode escape hatch
    return (
        defer(DocumentRow.ocr_text),
        selectinload(DocumentRow.extracted_fields),
    )


def light_user_checks_query(db: Session, user_id: str) -> Query:
    """Standard `CheckRow` query for the dashboard read paths.

    Returns checks for `user_id` with documents + extracted_fields
    eager-loaded and `ocr_text` deferred. Findings stay lazy because
    most code paths don't iterate them.
    """
    return (
        db.query(CheckRow)
        .filter(CheckRow.user_id == user_id)
        .options(
            selectinload(CheckRow.documents).options(*documents_loader_options()),
        )
    )
