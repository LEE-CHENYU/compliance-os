#!/usr/bin/env python3
"""Summarize persisted LLM API usage from the application database."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import sessionmaker

from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables_v2 import LlmApiUsageRow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report persisted LLM API usage.")
    parser.add_argument("--check-id", default=None, help="Optional check id filter.")
    parser.add_argument("--environment", default=None, help="Optional environment filter.")
    parser.add_argument("--provider", default=None, help="Optional provider filter.")
    parser.add_argument("--operation", default=None, help="Optional operation filter.")
    parser.add_argument("--days", type=int, default=None, help="Only include rows from the last N days.")
    parser.add_argument("--limit", type=int, default=20, help="Max recent rows to print.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    SessionLocal = sessionmaker(bind=get_engine())
    session = SessionLocal()
    try:
        query = session.query(LlmApiUsageRow)
        if args.check_id:
            query = query.filter(LlmApiUsageRow.check_id == args.check_id)
        if args.environment:
            query = query.filter(LlmApiUsageRow.environment == args.environment)
        if args.provider:
            query = query.filter(LlmApiUsageRow.provider == args.provider)
        if args.operation:
            query = query.filter(LlmApiUsageRow.operation == args.operation)
        if args.days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
            query = query.filter(LlmApiUsageRow.started_at >= cutoff)

        rows = (
            query.order_by(LlmApiUsageRow.started_at.desc(), LlmApiUsageRow.id.desc())
            .limit(args.limit)
            .all()
        )
        all_rows = query.all()

        by_environment = Counter(row.environment for row in all_rows)
        by_provider = Counter(row.provider for row in all_rows)
        by_model = Counter(row.model for row in all_rows)
        by_operation = Counter(row.operation for row in all_rows)
        by_status = Counter(row.status for row in all_rows)
        by_day = Counter((_iso(row.started_at) or "")[:10] for row in all_rows if row.started_at)

        payload = {
            "total_requests": len(all_rows),
            "successful_requests": by_status.get("success", 0),
            "failed_requests": len(all_rows) - by_status.get("success", 0),
            "input_tokens": sum(row.input_tokens or 0 for row in all_rows),
            "output_tokens": sum(row.output_tokens or 0 for row in all_rows),
            "total_tokens": sum(row.total_tokens or 0 for row in all_rows),
            "cache_creation_input_tokens": sum(
                row.cache_creation_input_tokens or 0 for row in all_rows
            ),
            "cache_read_input_tokens": sum(row.cache_read_input_tokens or 0 for row in all_rows),
            "by_environment": dict(by_environment),
            "by_provider": dict(by_provider),
            "by_model": dict(by_model),
            "by_operation": dict(by_operation),
            "by_status": dict(by_status),
            "by_day": dict(by_day),
            "recent_requests": [
                {
                    "id": row.id,
                    "check_id": row.check_id,
                    "document_id": row.document_id,
                    "user_id": row.user_id,
                    "environment": row.environment,
                    "provider": row.provider,
                    "model": row.model,
                    "operation": row.operation,
                    "status": row.status,
                    "input_tokens": row.input_tokens,
                    "output_tokens": row.output_tokens,
                    "total_tokens": row.total_tokens,
                    "cache_creation_input_tokens": row.cache_creation_input_tokens,
                    "cache_read_input_tokens": row.cache_read_input_tokens,
                    "latency_ms": row.latency_ms,
                    "error_type": row.error_type,
                    "error_message": row.error_message,
                    "request_metadata": row.request_metadata,
                    "usage_details": row.usage_details,
                    "started_at": _iso(row.started_at),
                    "completed_at": _iso(row.completed_at),
                }
                for row in rows
            ],
        }

        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Total requests: {payload['total_requests']}")
            print(f"Successful requests: {payload['successful_requests']}")
            print(f"Failed requests: {payload['failed_requests']}")
            print(f"Input tokens: {payload['input_tokens']}")
            print(f"Output tokens: {payload['output_tokens']}")
            print(f"Total tokens: {payload['total_tokens']}")
            print(f"Cache creation input tokens: {payload['cache_creation_input_tokens']}")
            print(f"Cache read input tokens: {payload['cache_read_input_tokens']}")
            print(f"By environment: {payload['by_environment']}")
            print(f"By provider: {payload['by_provider']}")
            print(f"By model: {payload['by_model']}")
            print(f"By operation: {payload['by_operation']}")
            print(f"By status: {payload['by_status']}")
            print(f"By day: {payload['by_day']}")
            print("Recent requests:")
            for row in payload["recent_requests"]:
                print(
                    f"- [{row['status']}] {row['environment']} {row['provider']} {row['model']} "
                    f"op={row['operation']} total_tokens={row['total_tokens']} latency_ms={row['latency_ms']}"
                )
                if row["error_type"]:
                    print(f"  error={row['error_type']}: {row['error_message']}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
