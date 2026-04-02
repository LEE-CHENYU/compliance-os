#!/usr/bin/env python3
"""Validate a batch manifest against the real source slice on disk."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from compliance_os.batch_validation import validate_batch_source_slice


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a data-room batch against real source files.")
    parser.add_argument(
        "--manifest",
        default=str(PROJECT_ROOT / "config" / "data_room_batches.yaml"),
        help="Path to the batch manifest YAML.",
    )
    parser.add_argument("--batch-number", type=int, default=None, help="Batch number to validate.")
    parser.add_argument("--batch-id", default=None, help="Batch id to validate.")
    parser.add_argument("--source-root", default=None, help="Optional source root override.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text summary.")
    return parser


def render_summary(payload: dict) -> str:
    checks = payload["checks"]
    passed = sum(1 for check in checks if check["ok"])
    lines = [
        f"Batch {payload['batch_number']:02d} {payload['batch_id']}",
        f"Focus: {payload['focus']}",
        f"Record: {payload['record']}",
        f"Source root: {payload['source_root']}",
        f"Manifest rows: {payload['manifest_rows']}",
        f"Target size: {payload['target_size']}",
        f"Real-source checks passed: {passed}/{len(checks)}",
    ]
    if payload["manifest_rows"] != payload["target_size"] and payload["target_size"] is not None:
        lines.append("Manifest row count does not match target size")
    for check in checks:
        status = "OK" if check["ok"] else "FAIL"
        line = f"- [{status}] {check['label']}: {check['file_path']} -> expected {check['expected_doc_type']}"
        if check["resolved_doc_type"] is not None:
            line += f", resolved {check['resolved_doc_type']}"
        lines.append(line)
        if check["error"]:
            lines.append(f"  error: {check['error']}")
    lines.append(f"Overall: {'PASS' if payload['ok'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.batch_number is None and not args.batch_id:
        parser.error("Provide --batch-number or --batch-id")

    summary = validate_batch_source_slice(
        project_root=PROJECT_ROOT,
        manifest_path=args.manifest,
        batch_number=args.batch_number,
        batch_id=args.batch_id,
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
