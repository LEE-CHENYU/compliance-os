#!/usr/bin/env python3
"""Rubric Loop — codex-backed evaluation harness for the compliance rule engine.

Usage:
    python scripts/rubric_loop.py                              # full run, cache-hit friendly
    python scripts/rubric_loop.py --only job_title_mismatch    # drill one rule
    python scripts/rubric_loop.py --slice A                    # positive cases only
    python scripts/rubric_loop.py --phases discover,evaluate   # skip generate + judge
    python scripts/rubric_loop.py --regen A                    # force regen slice A
    python scripts/rubric_loop.py --no-gen                     # skip generation
    python scripts/rubric_loop.py --no-judge                   # skip judge
    python scripts/rubric_loop.py --fail-fast                  # abort on first per-case error

See docs/superpowers/specs/2026-04-10-rubric-loop-design.md for design rationale.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from rubric.aggregate import assemble_scorecard, write_scorecard
from rubric.discover import build_manifest
from rubric.evaluate import evaluate_case
from rubric.generate import generate_missing
from rubric.io import (
    CONFIG_RULES_DIR,
    EVAL_CACHE_DIR,
    FIXTURE_DIR,
    GOLDENS_DIR,
    JUDGE_CACHE_DIR,
    ensure_dirs,
    load_json,
)
from rubric.judge import judge_case
from rubric.models import CallTelemetry, CaseSpec, CoverageGap, FixtureRecord

ALL_PHASES = ["discover", "generate", "evaluate", "judge", "aggregate"]
logger = logging.getLogger("rubric_loop")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Codex-backed rubric evaluation loop for the compliance rule engine.",
    )
    parser.add_argument("--phases", default=",".join(ALL_PHASES),
                        help="comma-separated list of phases to run")
    parser.add_argument("--only", default=None,
                        help="filter to cases for a single rule_id")
    parser.add_argument("--slice", dest="slices", action="append",
                        choices=["A", "B", "C", "D", "E"], default=None,
                        help="filter to specific slices (repeatable)")
    parser.add_argument("--regen", nargs="?", const="ALL", default=None,
                        help="force regenerate fixtures (optional slice letter)")
    parser.add_argument("--no-gen", action="store_true",
                        help="shorthand for --phases discover,evaluate,judge,aggregate")
    parser.add_argument("--no-judge", action="store_true",
                        help="shorthand for --phases discover,generate,evaluate,aggregate")
    parser.add_argument("--fail-fast", action="store_true",
                        help="abort on first per-case error")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args()


def _setup_logging(args) -> None:
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


def _resolve_phases(args) -> list[str]:
    if args.no_gen and args.no_judge:
        logger.error("--no-gen and --no-judge are contradictory")
        sys.exit(2)
    if args.no_gen:
        return ["discover", "evaluate", "judge", "aggregate"]
    if args.no_judge:
        return ["discover", "generate", "evaluate", "aggregate"]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()]
    for p in phases:
        if p not in ALL_PHASES:
            logger.error("unknown phase: %s", p)
            sys.exit(2)
    return phases


def _filter_manifest(manifest: list[CaseSpec], args) -> list[CaseSpec]:
    filtered = manifest
    if args.only:
        filtered = [c for c in filtered if c.target_rule_id == args.only]
    if args.slices:
        filtered = [c for c in filtered if c.slice in args.slices]
    if args.only and not filtered:
        logger.error("no cases match rule_id=%r. check config/rules/*.yaml", args.only)
        sys.exit(2)
    return filtered


def _load_fixture(case_id: str) -> FixtureRecord | None:
    path = FIXTURE_DIR / f"{case_id}.json"
    if not path.exists():
        path = GOLDENS_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    return FixtureRecord.from_dict(load_json(path))


def _apply_regen(args, manifest: list[CaseSpec]) -> None:
    if not args.regen:
        return
    if args.regen == "ALL":
        target_slices = {"A", "B"}
    else:
        if args.regen in {"C", "D", "E"}:
            logger.error("cannot regenerate static goldens; edit files in %s directly", GOLDENS_DIR)
            sys.exit(2)
        target_slices = {args.regen}
    for spec in manifest:
        if spec.slice in target_slices and spec.gen_strategy == "llm":
            fpath = FIXTURE_DIR / f"{spec.case_id}.json"
            if fpath.exists():
                fpath.unlink()
            evpath = EVAL_CACHE_DIR / f"{spec.case_id}.json"
            if evpath.exists():
                evpath.unlink()


def main() -> int:
    args = _parse_args()
    _setup_logging(args)
    phases = _resolve_phases(args)
    ensure_dirs(FIXTURE_DIR, GOLDENS_DIR, EVAL_CACHE_DIR, JUDGE_CACHE_DIR)

    telemetry = CallTelemetry()
    warnings: list[str] = []

    if "discover" in phases:
        try:
            manifest = build_manifest(CONFIG_RULES_DIR, GOLDENS_DIR)
        except CoverageGap as e:
            logger.error("coverage gap detected: %s", e)
            return 2
        logger.info("Phase 0 discover: manifest has %d cases", len(manifest))
    else:
        logger.error("discover phase is required (manifest must exist in-memory)")
        return 2

    manifest = _filter_manifest(manifest, args)
    _apply_regen(args, manifest)

    if "generate" in phases:
        logger.info("Phase 1 generate-missing: checking %d cases", len(manifest))
        new_count, skip_count, gen_warnings = generate_missing(
            manifest, fixture_dir=FIXTURE_DIR, rules_dir=CONFIG_RULES_DIR,
        )
        warnings.extend(gen_warnings)
        telemetry.generator_calls = new_count
        telemetry.generator_calls_cached = skip_count
        logger.info("Phase 1 generate-missing: %d new, %d cached, %d warnings",
                    new_count, skip_count, len(gen_warnings))

    eval_records: dict = {}
    if "evaluate" in phases:
        logger.info("Phase 2 evaluate: running engine on %d cases", len(manifest))
        for spec in manifest:
            fixture = _load_fixture(spec.case_id)
            if fixture is None:
                warnings.append(f"no fixture for {spec.case_id}; skipped")
                continue
            try:
                eval_records[spec.case_id] = evaluate_case(fixture)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"evaluate crashed for {spec.case_id}: {e}")
                if args.fail_fast:
                    return 1

    judge_records: dict = {}
    if "judge" in phases:
        logger.info("Phase 3 judge: grading %d cases", len(eval_records))
        for spec in manifest:
            eval_rec = eval_records.get(spec.case_id)
            fixture = _load_fixture(spec.case_id)
            if not fixture or not eval_rec:
                continue
            try:
                judge_records[spec.case_id] = judge_case(fixture, eval_rec)
            except Exception as e:  # noqa: BLE001
                warnings.append(f"judge crashed for {spec.case_id}: {e}")
                if args.fail_fast:
                    return 1

    if "aggregate" in phases:
        prior = None  # could load the most recent out/rubric-loop-*.json here
        sc = assemble_scorecard(
            cases=manifest,
            eval_records=eval_records,
            judge_records=judge_records,
            telemetry=telemetry,
            warnings=warnings,
            prior_scorecard=prior,
        )
        json_path, md_path = write_scorecard(sc)
        logger.info("Phase 4 aggregate: scorecard written to %s", md_path)
        print(json.dumps(sc.to_dict(), indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
