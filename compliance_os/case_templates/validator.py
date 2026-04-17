"""Reusable validation pipeline for case templates.

Any case template (H-1B, CPA, future ones) can be validated through this
single entry point. Used by:
  - tests (pytest imports `validate`)
  - CLI runners (`python -m compliance_os.case_templates.validator <template> <folder>`)
  - MCP tools (generic `case_active_search` in mcp_server.py)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from compliance_os.case_templates.h1b import H1B_TEMPLATE
from compliance_os.case_templates.cpa import CPA_TEMPLATE
from compliance_os.case_templates.matcher import (
    Report,
    format_report,
    match_folder,
)
from compliance_os.case_templates.schema import Template


TEMPLATES: dict[str, Template] = {
    "h1b": H1B_TEMPLATE,
    "h1b_petition": H1B_TEMPLATE,
    "cpa": CPA_TEMPLATE,
    "cpa_nr_entity": CPA_TEMPLATE,
}


@dataclass
class ValidationResult:
    template_id: str
    template_name: str
    folder: str
    files_scanned: int
    required_total: int
    required_matched: int
    optional_total: int
    optional_matched: int
    overall_pct: float
    coverage: dict[str, float]
    missing_required: list[dict]
    missing_optional: list[dict]
    misplaced: list[dict]
    lineage_issues: list[str]
    unmatched_files: list[str]
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_line(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.template_name} · "
            f"{self.required_matched}/{self.required_total} required "
            f"({self.overall_pct:.0f}%) · {self.files_scanned} files"
        )


def resolve_template(template_id: str) -> Template:
    tpl = TEMPLATES.get(template_id.lower())
    if tpl is None:
        raise KeyError(
            f"Unknown template '{template_id}'. Available: "
            f"{sorted(set(t.id for t in TEMPLATES.values()))}"
        )
    return tpl


def validate(
    template_id: str,
    folder: str | Path,
    require_full_required: bool = False,
) -> ValidationResult:
    """Run template matching against a folder, return a structured result.

    Args:
        template_id: template key ('h1b', 'cpa', or the full template.id).
        folder: absolute or ~-path to the case package folder.
        require_full_required: if True, result.passed is False whenever
            any required slot is missing. Otherwise passes when >=90%
            of required slots are matched.
    """
    template = resolve_template(template_id)
    report: Report = match_folder(folder, template)

    req_slots = [s for s in template.slots if s.required]
    opt_slots = [s for s in template.slots if not s.required]
    req_matched = sum(1 for s in req_slots if s.id in report.matched)
    opt_matched = sum(1 for s in opt_slots if s.id in report.matched)
    pct = (100 * req_matched / len(req_slots)) if req_slots else 100.0

    passed = (
        req_matched == len(req_slots)
        if require_full_required
        else pct >= 90.0
    )

    return ValidationResult(
        template_id=template.id,
        template_name=template.name,
        folder=str(Path(folder).expanduser().resolve()),
        files_scanned=report.files_scanned,
        required_total=len(req_slots),
        required_matched=req_matched,
        optional_total=len(opt_slots),
        optional_matched=opt_matched,
        overall_pct=pct,
        coverage={k: round(v, 4) for k, v in report.coverage.items()},
        missing_required=[
            {"id": s.id, "title": s.title, "section": s.section}
            for s in report.missing_required
        ],
        missing_optional=[
            {"id": s.id, "title": s.title, "section": s.section}
            for s in report.missing_optional
        ],
        misplaced=[
            {"file": f, "current_section": c, "expected_section": e}
            for f, c, e in report.misplaced
        ],
        lineage_issues=list(report.lineage_issues),
        unmatched_files=list(report.unmatched_files),
        passed=passed,
    )


def format_validation(result: ValidationResult, verbose: bool = False) -> str:
    """Human-readable validation report."""
    template = resolve_template(result.template_id)
    report = match_folder(result.folder, template)
    lines = [result.summary_line(), ""]
    lines.append(format_report(report, template, verbose=verbose))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
#  CLI: python -m compliance_os.case_templates.validator <template> <folder>
# ──────────────────────────────────────────────────────────────────


def _cli() -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(
        prog="python -m compliance_os.case_templates.validator",
        description="Validate a local folder against a case template.",
    )
    p.add_argument("template", choices=sorted(TEMPLATES.keys()))
    p.add_argument("folder")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--verbose", action="store_true", help="Show match reasons")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any required slot missing (default: >=90%%)",
    )
    args = p.parse_args()

    try:
        result = validate(
            args.template, args.folder, require_full_required=args.strict
        )
    except (KeyError, NotADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_validation(result, verbose=args.verbose))
    return 0 if result.passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
