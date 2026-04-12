"""Phase 2: run fixtures through the real rule engine and cache the results."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the repo root so we can import compliance_os.* from scripts/
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from compliance_os.web.services.rule_engine import EvaluationContext, RuleEngine

from rubric.io import (
    CONFIG_RULES_DIR,
    EVAL_CACHE_DIR,
    load_json,
    save_json,
    sha256_of_file,
    sha256_of_obj,
)
from rubric.models import EvalRecord, FixtureRecord


def evaluate_case(fixture: FixtureRecord, *, cache_dir: Path = EVAL_CACHE_DIR) -> EvalRecord:
    """Run one fixture through the engine, cache the result, return the record."""
    rule_file = CONFIG_RULES_DIR / f"{fixture.track}.yaml"
    if not rule_file.exists():
        return EvalRecord(
            case_id=fixture.case_id,
            engine_version="unknown",
            rule_file_path=str(rule_file),
            rule_file_hash="",
            input_hash=sha256_of_obj(fixture.input),
            evaluated_at=_now_iso(),
            derived={},
            findings=[],
            engine_error=f"rule file not found for track={fixture.track!r}: {rule_file}",
        )

    rule_file_hash = sha256_of_file(rule_file)
    input_hash = sha256_of_obj(fixture.input)

    # Check cache
    cached_path = cache_dir / f"{fixture.case_id}.json"
    if cached_path.exists():
        cached = load_json(cached_path)
        if (
            cached.get("input_hash") == input_hash
            and cached.get("rule_file_hash") == rule_file_hash
        ):
            return EvalRecord.from_dict(cached)

    try:
        engine = RuleEngine.from_yaml(rule_file)
        ctx = EvaluationContext(
            answers=fixture.input.get("answers", {}),
            extraction_a=fixture.input.get("extraction_a", {}),
            extraction_b=fixture.input.get("extraction_b", {}),
            comparisons=fixture.input.get("comparisons", {}),
        )
        raw_findings = engine.evaluate(ctx)
        findings = [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "action": f.action,
                "consequence": f.consequence,
                "immigration_impact": f.immigration_impact,
            }
            for f in raw_findings
        ]
        record = EvalRecord(
            case_id=fixture.case_id,
            engine_version=engine.version,
            rule_file_path=str(rule_file),
            rule_file_hash=rule_file_hash,
            input_hash=input_hash,
            evaluated_at=_now_iso(),
            derived={"is_nra": ctx.answers.get("is_nra", "no")},
            findings=findings,
            engine_error=None,
        )
    except Exception as e:  # noqa: BLE001 — we intentionally catch and record
        record = EvalRecord(
            case_id=fixture.case_id,
            engine_version="unknown",
            rule_file_path=str(rule_file),
            rule_file_hash=rule_file_hash,
            input_hash=input_hash,
            evaluated_at=_now_iso(),
            derived={},
            findings=[],
            engine_error=f"{type(e).__name__}: {e}",
        )

    save_json(cached_path, record.to_dict())
    return record


def load_eval_cache(case_id: str, cache_dir: Path = EVAL_CACHE_DIR) -> EvalRecord | None:
    path = cache_dir / f"{case_id}.json"
    if not path.exists():
        return None
    return EvalRecord.from_dict(load_json(path))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
