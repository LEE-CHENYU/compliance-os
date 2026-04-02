#!/usr/bin/env python3
"""Summarize persisted ingestion issues from the production database."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables_v2 import IngestionIssueRow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report persisted ingestion issues.")
    parser.add_argument("--check-id", default=None, help="Optional check id filter.")
    parser.add_argument("--limit", type=int, default=20, help="Max issue rows to print.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    SessionLocal = sessionmaker(bind=get_engine())
    session = SessionLocal()
    try:
        query = session.query(IngestionIssueRow)
        if args.check_id:
            query = query.filter(IngestionIssueRow.check_id == args.check_id)
        rows = (
            query.order_by(IngestionIssueRow.detected_at.desc(), IngestionIssueRow.id.desc())
            .limit(args.limit)
            .all()
        )
        all_rows = query.all()

        by_code = Counter(row.issue_code for row in all_rows)
        by_stage = Counter(row.stage for row in all_rows)
        by_severity = Counter(row.severity for row in all_rows)
        by_doc_type = Counter()
        by_mime_type = Counter()
        by_extension = Counter()

        for row in all_rows:
            details = row.details or {}
            if details.get("doc_type"):
                by_doc_type[details["doc_type"]] += 1
            if details.get("mime_type"):
                by_mime_type[details["mime_type"]] += 1
            filename = details.get("filename") or details.get("source_path")
            if filename:
                by_extension[Path(filename).suffix.lower() or "[no_ext]"] += 1

        payload = {
            "total_issues": len(all_rows),
            "by_code": dict(by_code),
            "by_stage": dict(by_stage),
            "by_severity": dict(by_severity),
            "by_doc_type": dict(by_doc_type),
            "by_mime_type": dict(by_mime_type),
            "by_extension": dict(by_extension),
            "recent_issues": [
                {
                    "id": row.id,
                    "check_id": row.check_id,
                    "document_id": row.document_id,
                    "stage": row.stage,
                    "issue_code": row.issue_code,
                    "severity": row.severity,
                    "message": row.message,
                    "details": row.details,
                    "detected_at": row.detected_at.isoformat() if row.detected_at else None,
                }
                for row in rows
            ],
        }

        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Total issues: {payload['total_issues']}")
            print(f"By severity: {payload['by_severity']}")
            print(f"By stage: {payload['by_stage']}")
            print(f"By code: {payload['by_code']}")
            print(f"By doc type: {payload['by_doc_type']}")
            print(f"By mime type: {payload['by_mime_type']}")
            print(f"By extension: {payload['by_extension']}")
            print("Recent issues:")
            for row in payload["recent_issues"]:
                print(
                    f"- [{row['severity']}] {row['issue_code']} "
                    f"check={row['check_id']} doc={row['document_id']} stage={row['stage']}"
                )
                print(f"  {row['message']}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
