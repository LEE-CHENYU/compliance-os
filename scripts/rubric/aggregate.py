"""Phase 4: assemble per-run scorecard from cached fixtures + eval + judge records."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import yaml

from rubric.io import CONFIG_RUBRIC_DIR, OUT_DIR, save_json
from rubric.models import (
    CallTelemetry,
    CaseSpec,
    EvalRecord,
    JudgeRecord,
    Scorecard,
)


def classify_verdict_from_subscores(
    subscores: dict,
    weights: dict,
    hard_fail_criteria: list,
    *,
    pass_t: float,
    partial_t: float,
) -> str:
    # Hard-fail check: if any score for a hard-fail criterion is 0.0, verdict = fail
    for dim_scores in subscores.values():
        for crit_id in dim_scores.get("criteria_applied", []):
            if crit_id in hard_fail_criteria and dim_scores.get("score", 1.0) == 0.0:
                return "fail"

    if not subscores:
        return "unrunnable"

    total_weight = 0.0
    weighted_sum = 0.0
    for dim, body in subscores.items():
        w = weights.get(dim, 1.0)
        total_weight += w
        weighted_sum += w * body.get("score", 0.0)
    if total_weight == 0:
        return "unrunnable"
    weighted_mean = weighted_sum / total_weight

    if weighted_mean >= pass_t:
        return "pass"
    if weighted_mean >= partial_t:
        return "partial"
    return "fail"


def compute_totals(judge_records: list[JudgeRecord]) -> dict:
    totals = {"cases": 0, "pass": 0, "partial": 0, "fail": 0, "unrunnable": 0}
    for r in judge_records:
        totals["cases"] += 1
        v = r.verdict
        if v in totals:
            totals[v] += 1
        else:
            totals["unrunnable"] += 1
    return totals


def _by_group(records: list[JudgeRecord], cases: list[CaseSpec], key: str) -> dict:
    """Group verdict counts by a CaseSpec attribute (e.g., 'track', 'slice')."""
    case_by_id = {c.case_id: c for c in cases}
    out: dict = {}
    for r in records:
        c = case_by_id.get(r.case_id)
        if not c:
            continue
        k = getattr(c, key, None)
        if not k:
            continue
        bucket = out.setdefault(k, {"cases": 0, "pass": 0, "partial": 0, "fail": 0, "unrunnable": 0})
        bucket["cases"] += 1
        if r.verdict in bucket:
            bucket[r.verdict] += 1
        else:
            bucket["unrunnable"] += 1
    return out


def _by_dimension(judge_records: list[JudgeRecord]) -> dict:
    out: dict = {}
    for r in judge_records:
        for dim, body in r.subscores.items():
            b = out.setdefault(dim, {"scores": [], "cases": 0})
            b["scores"].append(body.get("score", 0.0))
            b["cases"] += 1
    return {
        dim: {"weighted_mean": round(mean(b["scores"]), 3), "cases": b["cases"]}
        for dim, b in out.items()
    }


def _failure_details(
    judge_records: list[JudgeRecord],
    cases: list[CaseSpec],
) -> list[dict]:
    failures: list[dict] = []
    for r in judge_records:
        if r.verdict != "fail":
            continue
        dim_scores = {dim: round(body.get("score", 0.0), 2) for dim, body in r.subscores.items()}
        hard_fail = None
        for dim, body in r.subscores.items():
            if body.get("score") == 0.0 and body.get("criteria_applied"):
                hard_fail = body["criteria_applied"][0]
                break
        failures.append({
            "case_id": r.case_id,
            "verdict": r.verdict,
            "dimension_scores": dim_scores,
            "hard_fail_criterion": hard_fail,
            "judge_note": _first_note(r.subscores),
            "flags": list(r.flags),
        })
    return failures


def _first_note(subscores: dict) -> str:
    for body in subscores.values():
        note = body.get("note")
        if note:
            return note
    return ""


def assemble_scorecard(
    *,
    cases: list[CaseSpec],
    eval_records: dict,  # case_id -> EvalRecord
    judge_records: dict,  # case_id -> JudgeRecord
    telemetry: CallTelemetry,
    warnings: list[str],
    prior_scorecard: dict | None = None,
) -> Scorecard:
    """Assemble a Scorecard dataclass from Phase 2+3 outputs."""
    criteria_data = yaml.safe_load((CONFIG_RUBRIC_DIR / "criteria.yaml").read_text())
    rubric_version = (CONFIG_RUBRIC_DIR / "rubric_version.txt").read_text().strip()

    judge_list = list(judge_records.values())
    totals = compute_totals(judge_list)
    by_track = _by_group(judge_list, cases, "track")
    by_slice = _by_group(judge_list, cases, "slice")
    by_dim = _by_dimension(judge_list)
    failures = _failure_details(judge_list, cases)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    engine_version = next(
        (r.engine_version for r in eval_records.values() if r.engine_version != "unknown"),
        "unknown",
    )

    delta: dict = {}
    if prior_scorecard:
        prior_verdicts = {}
        for entry in prior_scorecard.get("failures", []):
            prior_verdicts[entry["case_id"]] = entry["verdict"]
        new_failures = [r.case_id for r in judge_list
                        if r.verdict == "fail" and prior_verdicts.get(r.case_id) != "fail"]
        delta = {
            "last_run_id": prior_scorecard.get("run_id", ""),
            "new_failures": new_failures,
            "new_passes": [],
            "new_unrunnable": [],
            "rules_with_score_change": [],
            "unchanged_cases": max(0, totals["cases"] - len(new_failures)),
        }

    return Scorecard(
        run_id=now,
        engine_version=engine_version,
        rubric_version=rubric_version,
        codex_version="0.118.0",
        codex_model="gpt-5.4",
        reasoning_effort="xhigh",
        started_at=now,
        completed_at=now,
        totals=totals,
        by_track=by_track,
        by_slice=by_slice,
        by_dimension=by_dim,
        failures=failures,
        coverage_gaps=[],
        warnings=warnings,
        delta_from_last_run=delta,
        telemetry={
            "generator_calls": telemetry.generator_calls,
            "generator_calls_cached": telemetry.generator_calls_cached,
            "judge_calls": telemetry.judge_calls,
            "judge_calls_cached": telemetry.judge_calls_cached,
            "tokens_in_total": telemetry.tokens_in_total,
            "tokens_out_total": telemetry.tokens_out_total,
            "note": "codex CLI usage is subscription-billed; token counts are for prompt-tuning only",
        },
    )


def render_scorecard_markdown(sc: Scorecard) -> str:
    """Short human-readable version for out/rubric-loop-<ts>.md."""
    t = sc.totals
    lines = [
        f"# Rubric Loop — {sc.run_id}",
        "",
        f"**Totals:** {t['pass']} pass / {t['partial']} partial / {t['fail']} fail / {t['unrunnable']} unrunnable   ({t['cases']} cases)",
        f"**Engine:** {sc.engine_version}   **Rubric:** {sc.rubric_version}   **Model:** {sc.codex_model} ({sc.reasoning_effort})",
        "",
    ]
    if sc.delta_from_last_run.get("new_failures"):
        lines.append("## Delta from last run")
        for case_id in sc.delta_from_last_run["new_failures"]:
            lines.append(f"- NEW FAIL: `{case_id}`")
        lines.append("")
    lines.append("## By track")
    lines.append("| track | cases | pass | partial | fail | unrunnable |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for track, b in sorted(sc.by_track.items()):
        lines.append(f"| {track} | {b['cases']} | {b['pass']} | {b['partial']} | {b['fail']} | {b['unrunnable']} |")
    lines.append("")
    lines.append("## By slice")
    lines.append("| slice | cases | pass | partial | fail | unrunnable |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for slice_, b in sorted(sc.by_slice.items()):
        lines.append(f"| {slice_} | {b['cases']} | {b['pass']} | {b['partial']} | {b['fail']} | {b['unrunnable']} |")
    lines.append("")
    lines.append("## By dimension (weighted mean)")
    lines.append("| dimension | weighted_mean | cases |")
    lines.append("|---|---:|---:|")
    for dim, b in sorted(sc.by_dimension.items()):
        lines.append(f"| {dim} | {b['weighted_mean']} | {b['cases']} |")
    lines.append("")
    if sc.failures:
        lines.append("## Failures")
        for f in sc.failures:
            lines.append(f"### {f['case_id']} ({f['verdict']})")
            if f.get("hard_fail_criterion"):
                lines.append(f"- **Hard-fail:** `{f['hard_fail_criterion']}` scored 0.0")
            if f.get("judge_note"):
                lines.append(f"- **Judge note:** {f['judge_note']}")
            if f.get("flags"):
                lines.append(f"- **Flags:** {', '.join(f['flags'])}")
            lines.append(f"- **Fixture:** `scripts/rubric_fixtures/{f['case_id']}.json`")
            lines.append("")
    if sc.warnings:
        lines.append("## Warnings")
        for w in sc.warnings:
            lines.append(f"- {w}")
        lines.append("")
    return "\n".join(lines)


def write_scorecard(sc: Scorecard) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = sc.run_id.replace(":", "-")
    json_path = OUT_DIR / f"rubric-loop-{ts}.json"
    md_path = OUT_DIR / f"rubric-loop-{ts}.md"
    save_json(json_path, sc.to_dict())
    md_path.write_text(render_scorecard_markdown(sc))
    return json_path, md_path
