#!/usr/bin/env python3
"""Copy Compliance OS data from a SQLite database into Postgres."""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, delete, func, inspect, insert, select, text

from compliance_os.web.models.auth import UserRow  # noqa: F401
from compliance_os.web.models.database import Base, create_engine_and_tables
from compliance_os.web.models.tables import (  # noqa: F401
    CaseRow,
    ChatMessageRow,
    DiscoveryAnswerRow,
    DocumentRow as LegacyDocumentRow,
)
from compliance_os.web.models.tables_v2 import Base as BaseV2  # noqa: F401
from compliance_os.web.models.tables_v2 import (  # noqa: F401
    CheckRow,
    ComparisonRow,
    DocumentRow,
    ExtractedFieldRow,
    FindingRow,
    FollowupRow,
    IngestionIssueRow,
    LlmApiUsageRow,
)

TABLE_ORDER = [
    "users",
    "cases",
    "checks",
    "documents",
    "documents_v2",
    "discovery_answers",
    "chat_messages",
    "extracted_fields",
    "ingestion_issues",
    "llm_api_usage",
    "comparisons",
    "followups",
    "findings",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate Compliance OS SQLite data into Postgres.")
    parser.add_argument("--source-sqlite", required=True, help="Path to the SQLite database file.")
    parser.add_argument(
        "--dest-url",
        required=True,
        help="Destination SQLAlchemy Postgres URL, usually DATABASE_DIRECT_URL.",
    )
    parser.add_argument(
        "--truncate-dest",
        action="store_true",
        help="Delete existing destination rows before copying.",
    )
    parser.add_argument(
        "--allow-nonempty-dest",
        action="store_true",
        help="Allow copying into a non-empty destination without truncation.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Insert batch size for each table.",
    )
    return parser


def _normalize_dest_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://"):]
    if normalized.startswith("postgresql://"):
        normalized = "postgresql+psycopg://" + normalized[len("postgresql://"):]
    return normalized


def _table_counts(conn, table_names: list[str]) -> dict[str, int]:
    metadata = MetaData()
    counts: dict[str, int] = {}
    for table_name in table_names:
        table = Table(table_name, metadata, autoload_with=conn)
        counts[table_name] = conn.execute(select(func.count()).select_from(table)).scalar_one()
    return counts


def _fetch_source_rows(source_engine, table_name: str) -> list[dict]:
    table = Base.metadata.tables.get(table_name)
    if table is None:
        table = BaseV2.metadata.tables.get(table_name)
    if table is None:
        raise KeyError(f"Unknown table {table_name}")
    with source_engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(table)).mappings()]


def _copy_table(dest_conn, table_name: str, rows: list[dict], batch_size: int) -> int:
    if not rows:
        return 0
    table = Table(table_name, MetaData(), autoload_with=dest_conn)
    inserted = 0
    for idx in range(0, len(rows), batch_size):
        batch = rows[idx : idx + batch_size]
        dest_conn.execute(insert(table), batch)
        inserted += len(batch)
    return inserted


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path = Path(args.source_sqlite).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Source SQLite database not found: {source_path}")

    source_engine = create_engine(f"sqlite:///{source_path}")
    source_tables = set(inspect(source_engine).get_table_names())

    dest_url = _normalize_dest_url(args.dest_url)
    dest_engine = create_engine_and_tables(dest_url)
    dest_tables = set(inspect(dest_engine).get_table_names())

    active_tables = [name for name in TABLE_ORDER if name in dest_tables]

    with dest_engine.begin() as dest_conn:
        existing_counts = _table_counts(dest_conn, active_tables)
        has_existing_rows = any(count > 0 for count in existing_counts.values())

        if has_existing_rows and not args.truncate_dest and not args.allow_nonempty_dest:
            raise SystemExit(
                "Destination database is not empty. Use --truncate-dest or --allow-nonempty-dest."
            )

        if args.truncate_dest:
            for table_name in reversed(active_tables):
                table = Table(table_name, MetaData(), autoload_with=dest_conn)
                dest_conn.execute(delete(table))

        inserted_counts: dict[str, int] = {}
        for table_name in active_tables:
            if table_name not in source_tables:
                inserted_counts[table_name] = 0
                continue
            rows = _fetch_source_rows(source_engine, table_name)
            inserted_counts[table_name] = _copy_table(dest_conn, table_name, rows, args.batch_size)

    with source_engine.connect() as source_conn:
        source_counts = {
            table_name: (
                source_conn.execute(
                    select(func.count()).select_from(
                        Table(table_name, MetaData(), autoload_with=source_conn)
                    )
                ).scalar_one()
                if table_name in source_tables
                else 0
            )
            for table_name in active_tables
        }

    with dest_engine.connect() as dest_conn:
        final_counts = _table_counts(dest_conn, active_tables)

    print("Migration complete.")
    for table_name in active_tables:
        print(
            f"{table_name}: source={source_counts.get(table_name, 0)} "
            f"inserted={inserted_counts.get(table_name, 0)} "
            f"dest={final_counts.get(table_name, 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
