"""Run the Claude-judged quality loop against the check services.

For each scenario in scripts/check_quality/scenarios.py:
  1. Invoke the real check service (process_X_check) with the synthetic intake.
  2. Send (intake, service output, rubric) to Claude Opus 4.6.
  3. Collect the verdict.
  4. Aggregate + render markdown to out/check-quality-report.md.

Caches by (scenario_id, output_hash, rubric_version) so unchanged outputs
skip the API call.

Usage:
  python scripts/check_quality_loop.py            # full run, all services
  python scripts/check_quality_loop.py h1b_doc_check  # filter by service
  python scripts/check_quality_loop.py --force    # bypass cache
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compliance_os.web.services.election_83b import process_election_83b
from compliance_os.web.services.fbar_check import process_fbar_check
from compliance_os.web.services.h1b_doc_check import (
    process_h1b_doc_check,
    save_uploaded_document,
)
from compliance_os.web.services.student_tax_check import process_student_tax_check

from scripts.check_quality.aggregate import Scorecard, render_markdown
from scripts.check_quality.judge import JudgeVerdict, judge_case
from scripts.check_quality.rubrics import get_rubric
from scripts.check_quality.scenarios import Scenario, all_scenarios


def _run_service(scenario: Scenario) -> tuple[dict, dict]:
    """Invoke the real check service. Returns (actual_intake, service_output).

    For H-1B, materializes text docs on disk first since the service reads
    file paths.
    """
    if scenario.service == "h1b_doc_check":
        from scripts.check_quality.scenarios import _h1b_material_doc
        docs = [
            _h1b_material_doc(scenario.case_id, doc_type, fields, save_uploaded_document)
            for (doc_type, fields) in scenario.intake["_docs"]
        ]
        intake = {"documents": docs}
        result = process_h1b_doc_check(scenario.case_id, intake, today=scenario.today or date.today())
        # For the judge, show the original scenario intake (doc-type + fields),
        # not the file-path intake — it's more readable.
        judge_intake = {
            "documents_uploaded": [
                {"doc_type": dt, "fields": fields}
                for (dt, fields) in scenario.intake["_docs"]
            ],
        }
        return judge_intake, result

    if scenario.service == "fbar_check":
        return scenario.intake, process_fbar_check(scenario.case_id, scenario.intake)

    if scenario.service == "student_tax_1040nr":
        return scenario.intake, process_student_tax_check(scenario.case_id, scenario.intake)

    if scenario.service == "election_83b":
        return (
            scenario.intake,
            process_election_83b(scenario.case_id, scenario.intake, today=scenario.today or date.today()),
        )

    raise ValueError(f"Unknown service: {scenario.service}")


def _strip_noisy_fields(service_output: dict) -> dict:
    """Remove paths and other non-judge-relevant fields from the service output."""
    cleaned = dict(service_output)
    if "artifacts" in cleaned:
        cleaned["artifacts"] = [
            {k: v for k, v in art.items() if k != "path"}
            for art in cleaned["artifacts"]
        ]
    if "document_summary" in cleaned:
        # Keep fields but drop filenames (internal)
        cleaned["document_summary"] = [
            {"doc_type": d["doc_type"], "fields": d["fields"]}
            for d in cleaned["document_summary"]
        ]
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Claude-judged quality loop for check services.")
    parser.add_argument("service", nargs="?", help="Filter to one service (h1b_doc_check, fbar_check, ...)")
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    parser.add_argument(
        "--mode",
        choices=["standard", "adversarial", "both"],
        default="standard",
        help="Which rubric(s) to run. 'both' runs each scenario under standard + adversarial rubrics.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "out" / "check-quality-report.md"),
        help="Where to write the markdown scorecard",
    )
    args = parser.parse_args()

    scenarios = all_scenarios()
    if args.service:
        scenarios = [s for s in scenarios if s.service == args.service]
        if not scenarios:
            print(f"No scenarios for service '{args.service}'")
            sys.exit(2)

    client = anthropic.Anthropic()
    verdicts: list[JudgeVerdict] = []
    total_in = total_out = 0

    rubric_modes: list[tuple[str, bool]] = []
    if args.mode in ("standard", "both"):
        rubric_modes.append(("standard", False))
    if args.mode in ("adversarial", "both"):
        rubric_modes.append(("adversarial", True))

    print(f"Running {len(scenarios)} scenarios × {len(rubric_modes)} rubric(s)...")
    for scenario in scenarios:
        judge_intake, service_output = _run_service(scenario)
        cleaned_output = _strip_noisy_fields(service_output)
        for mode_label, is_adversarial in rubric_modes:
            rubric = get_rubric(scenario.service, adversarial=is_adversarial)
            variant_case_id = f"{scenario.case_id}__{mode_label}"
            variant_label = f"{scenario.label} [{mode_label}]"
            print(f"  - {variant_case_id}... ", end="", flush=True)
            verdict = judge_case(
                scenario_id=variant_case_id,
                service=scenario.service,
                scenario_label=variant_label,
                scenario_description=scenario.description,
                intake=judge_intake,
                service_output=cleaned_output,
                rubric=rubric,
                client=client,
                force=args.force,
            )
            verdicts.append(verdict)
            total_in += verdict.tokens_in
            total_out += verdict.tokens_out
            cache_tag = " (cached)" if verdict.cached else ""
            print(f"{verdict.overall}{cache_tag}")

    scorecard = Scorecard(verdicts=verdicts, total_tokens_in=total_in, total_tokens_out=total_out)
    markdown = render_markdown(scorecard)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print()
    print(f"Scorecard: {scorecard.pass_count} pass · {scorecard.partial_count} partial · {scorecard.fail_count} fail")
    print(f"Tokens: {total_in:,} in · {total_out:,} out")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
