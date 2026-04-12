"""Phase 3: LLM-as-judge grading of engine output against declarative rubric criteria."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from rubric.codex_client import MODEL, call_codex
from rubric.io import (
    CONFIG_RUBRIC_DIR,
    JUDGE_CACHE_DIR,
    PROJECT_ROOT,
    load_json,
    save_json,
    sha256_of_obj,
    sha256_of_text,
)
from rubric.models import CodexCallError, EvalRecord, FixtureRecord, JudgeRecord

JUDGE_SCHEMA = PROJECT_ROOT / "scripts" / "rubric" / "schemas" / "judge-output.schema.json"
JUDGE_TEMPLATE = PROJECT_ROOT / "scripts" / "rubric" / "prompts" / "judge.md"


def _load_criteria() -> dict:
    return yaml.safe_load((CONFIG_RUBRIC_DIR / "criteria.yaml").read_text())


def _rubric_version() -> str:
    return (CONFIG_RUBRIC_DIR / "rubric_version.txt").read_text().strip()


def filter_criteria_for_slice(criteria: list[dict], slice_: str) -> list[dict]:
    return [c for c in criteria if slice_ in c.get("applies_to", [])]


def compute_judge_cache_key(
    input_hash: str,
    findings_hash: str,
    rubric_version: str,
    judge_prompt_hash: str,
) -> str:
    return sha256_of_text(
        f"{input_hash}|{findings_hash}|{rubric_version}|{judge_prompt_hash}"
    )


def render_judge_prompt(fixture: FixtureRecord, eval_record: EvalRecord) -> str:
    template = JUDGE_TEMPLATE.read_text()
    criteria = _load_criteria().get("criteria", [])
    filtered = filter_criteria_for_slice(criteria, fixture.slice)
    criteria_yaml = yaml.safe_dump(filtered, sort_keys=False)
    return (
        template
        .replace("{case_fixture_json}", json.dumps(fixture.to_dict(), indent=2))
        .replace("{derived_is_nra}", eval_record.derived.get("is_nra", "unknown"))
        .replace("{findings_json}", json.dumps(eval_record.findings, indent=2))
        .replace("{engine_error_or_none}", eval_record.engine_error or "(none)")
        .replace("{slice}", fixture.slice)
        .replace("{filtered_criteria_yaml}", criteria_yaml)
    )


def judge_case(
    fixture: FixtureRecord,
    eval_record: EvalRecord,
    *,
    cache_dir: Path = JUDGE_CACHE_DIR,
) -> JudgeRecord:
    """Grade one case. Cached by (input_hash, findings_hash, rubric_version, prompt_hash)."""
    rubric_version = _rubric_version()
    findings_hash = sha256_of_obj(eval_record.findings)
    prompt = render_judge_prompt(fixture, eval_record)
    prompt_hash = sha256_of_text(prompt)
    cache_key = compute_judge_cache_key(
        eval_record.input_hash, findings_hash, rubric_version, prompt_hash
    )

    cached_path = cache_dir / f"{cache_key}.json"
    if cached_path.exists():
        return JudgeRecord.from_dict(load_json(cached_path))

    try:
        result = call_codex(prompt=prompt, schema_path=JUDGE_SCHEMA)
    except CodexCallError as e:
        record = JudgeRecord(
            cache_key=cache_key,
            cache_key_inputs={
                "case_id": fixture.case_id,
                "input_hash": eval_record.input_hash,
                "findings_hash": findings_hash,
                "rubric_version": rubric_version,
                "judge_prompt_hash": prompt_hash,
            },
            case_id=fixture.case_id,
            judged_at=_now_iso(),
            judged_by=f"codex-cli/{MODEL}",
            verdict="unrunnable",
            subscores={},
            flags=[f"judge_error:{e.kind}"],
            raw_judge_output=e.message,
        )
        save_json(cached_path, record.to_dict())
        return record

    parsed = result.parsed
    record = JudgeRecord(
        cache_key=cache_key,
        cache_key_inputs={
            "case_id": fixture.case_id,
            "input_hash": eval_record.input_hash,
            "findings_hash": findings_hash,
            "rubric_version": rubric_version,
            "judge_prompt_hash": prompt_hash,
        },
        case_id=fixture.case_id,
        judged_at=_now_iso(),
        judged_by=f"codex-cli/{MODEL}",
        verdict=parsed["verdict"],
        subscores=parsed["subscores"],
        flags=parsed.get("flags", []),
        raw_judge_output=result.text,
    )
    save_json(cached_path, record.to_dict())
    return record


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
