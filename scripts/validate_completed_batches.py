#!/usr/bin/env python3
"""Retro-validate completed data-room batches against the real source tree."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compliance_os.batch_validation import validate_batch_collection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate completed data-room batches against the real source files.")
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "config" / "data_room_batches.yaml"),
        help="Path to the batch manifest YAML.",
    )
    parser.add_argument("--min-batch-number", type=int, default=None, help="Optional lower batch bound.")
    parser.add_argument("--max-batch-number", type=int, default=None, help="Optional upper batch bound.")
    parser.add_argument(
        "--batch-number",
        type=int,
        action="append",
        dest="batch_numbers",
        help="Specific batch number to validate. Can be passed multiple times.",
    )
    parser.add_argument(
        "--include-status",
        action="append",
        dest="statuses",
        help="Manifest statuses to include. Defaults to completed only.",
    )
    parser.add_argument("--source-root", default=None, help="Optional source root override.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text summary.")
    return parser


def render_summary(payload: dict) -> str:
    lines = [
        f"Source root: {payload['source_root']}",
        f"Selected batches: {payload['total_batches']}",
        f"Passed batches: {payload['passed_batches']}/{payload['total_batches']}",
    ]
    for summary in payload["selected_batches"]:
        passed = sum(1 for check in summary["checks"] if check["ok"])
        lines.append(
            f"- Batch {summary['batch_number']:02d} {summary['batch_id']}: "
            f"{passed}/{len(summary['checks'])} real-source checks"
        )
    lines.append(f"Overall: {'PASS' if payload['ok'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    statuses = set(args.statuses or ["completed"])
    batch_numbers = set(args.batch_numbers or []) or None

    summary = validate_batch_collection(
        project_root=PROJECT_ROOT,
        manifest_path=args.manifest,
        statuses=statuses,
        min_batch_number=args.min_batch_number,
        max_batch_number=args.max_batch_number,
        batch_numbers=batch_numbers,
        source_root_override=args.source_root,
    )
    payload = summary.to_dict()

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_summary(payload))

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
