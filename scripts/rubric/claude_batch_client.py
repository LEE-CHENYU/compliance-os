"""Claude Message Batches API backend for the rubric loop.

Submits all generator or judge prompts as one batch per phase, polls for
completion, parses results into FixtureRecord / JudgeRecord objects.

Contract-compatible with the existing codex CLI backend: returns the same
(new_count, skip_count, warnings) tuple for generator, same {case_id:
JudgeRecord} dict for judge. Failed requests produce sentinel fixtures or
unrunnable JudgeRecords, matching codex backend failure semantics.

V0 limitations (TODO for a follow-up):
  * Prompt caching is NOT enabled. render_generator_prompt() and
    render_judge_prompt() currently return a single interleaved string
    mixing static template content with variable per-case content. A
    follow-up can split those templates into a static system prefix (with
    cache_control) + variable user message to cut cost by ~50% more on
    top of the existing 50% batch discount.
  * Per-slice criteria caching is deferred — all judge requests go out as
    independent cache blocks.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from rubric.generate import detect_pii_shaped_strings, render_generator_prompt
from rubric.io import save_json, sha256_of_obj, sha256_of_text
from rubric.judge import (
    _rubric_version,
    compute_judge_cache_key,
    render_judge_prompt,
)
from rubric.models import (
    CaseSpec,
    EvalRecord,
    FixtureRecord,
    JudgeRecord,
)

DEFAULT_GENERATOR_MODEL = "claude-sonnet-4-5"
DEFAULT_JUDGE_MODEL = "claude-opus-4-6"
POLL_INTERVAL_SECONDS = 60
MAX_WAIT_SECONDS = 24 * 3600  # 24 hours per Anthropic docs

GENERATOR_MODEL = os.environ.get("RUBRIC_CLAUDE_GENERATOR_MODEL", DEFAULT_GENERATOR_MODEL)
JUDGE_MODEL = os.environ.get("RUBRIC_CLAUDE_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_generator_request(spec: CaseSpec, rules_dir: Path) -> Request:
    """Build a Request for a single generator case. No caching in v0."""
    prompt = render_generator_prompt(spec, rules_dir=rules_dir)
    return Request(
        custom_id=f"gen-{spec.case_id}",
        params=MessageCreateParamsNonStreaming(
            model=GENERATOR_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        ),
    )


def _build_judge_request(fixture: FixtureRecord, eval_record: EvalRecord) -> Request:
    """Build a Request for a single judge case with Opus adaptive thinking."""
    prompt = render_judge_prompt(fixture, eval_record)
    return Request(
        custom_id=f"judge-{fixture.case_id}",
        params=MessageCreateParamsNonStreaming(
            model=JUDGE_MODEL,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        ),
    )


def _poll_until_ended(client: anthropic.Anthropic, batch_id: str) -> None:
    """Block until the batch's processing_status is 'ended' or raise TimeoutError."""
    start = time.monotonic()
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return
        if time.monotonic() - start > MAX_WAIT_SECONDS:
            raise TimeoutError(
                f"batch {batch_id} exceeded {MAX_WAIT_SECONDS}s timeout"
            )
        time.sleep(POLL_INTERVAL_SECONDS)


def _make_sentinel_fixture(spec: CaseSpec, result, error_msg: str = "") -> dict:
    """Build a sentinel fixture dict for a failed generation."""
    err_kind = "unknown"
    err_message = error_msg
    if result is not None and getattr(result.result, "type", None) == "errored":
        err = getattr(result.result, "error", None)
        if err is not None:
            err_kind = getattr(err, "type", "unknown")
            err_message = getattr(err, "message", err_message)
    return {
        "case_id": spec.case_id,
        "slice": spec.slice,
        "track": spec.track,
        "target_rule_id": spec.target_rule_id,
        "probe_intent": spec.probe_intent,
        "generated_by": f"claude-batch/{GENERATOR_MODEL}",
        "generated_at": _now_iso(),
        "generator_prompt_hash": None,
        "flavor_hint": None,
        "input": {
            "answers": {},
            "extraction_a": {},
            "extraction_b": {},
            "comparisons": {},
        },
        "expected": {
            "must_fire_rule_ids": [],
            "must_not_fire_rule_ids": [],
            "expected_nra": "no",
            "expected_track": spec.track,
            "notes": f"GENERATION FAILED: {err_kind}",
        },
        "last_error": {"kind": err_kind, "message": err_message},
    }


def batch_generate(
    specs_to_generate: list[CaseSpec],
    *,
    rules_dir: Path,
    fixture_dir: Path,
    client: anthropic.Anthropic | None = None,
) -> tuple[int, int, list[str]]:
    """Submit all LLM generator prompts as one batch, poll, parse, write fixtures.

    Returns (new_count, skip_count, warnings). Same contract as
    rubric.generate.generate_missing() but with only one external call
    (the batch submission) instead of N per-case codex calls.

    Skips:
      * specs with gen_strategy != "llm" (goldens)
      * specs whose fixture file already exists on disk
    """
    if client is None:
        client = anthropic.Anthropic()

    fixture_dir.mkdir(parents=True, exist_ok=True)

    to_run: list[CaseSpec] = []
    skip_count = 0
    for spec in specs_to_generate:
        if spec.gen_strategy != "llm":
            skip_count += 1
            continue
        target_path = fixture_dir / f"{spec.case_id}.json"
        if target_path.exists():
            skip_count += 1
            continue
        to_run.append(spec)

    if not to_run:
        return 0, skip_count, []

    requests = [_build_generator_request(spec, rules_dir) for spec in to_run]
    spec_by_custom_id = {f"gen-{spec.case_id}": spec for spec in to_run}

    message_batch = client.messages.batches.create(requests=requests)
    _poll_until_ended(client, message_batch.id)

    new_count = 0
    warnings: list[str] = []
    for result in client.messages.batches.results(message_batch.id):
        spec = spec_by_custom_id.get(result.custom_id)
        if spec is None:
            warnings.append(f"unknown custom_id in results: {result.custom_id}")
            continue
        target_path = fixture_dir / f"{spec.case_id}.json"

        if result.result.type != "succeeded":
            err_kind = result.result.type
            err = getattr(result.result, "error", None)
            if err is not None:
                err_kind = getattr(err, "type", err_kind) or err_kind
            warnings.append(
                f"generator failed for {spec.case_id}: {err_kind}"
            )
            save_json(target_path, _make_sentinel_fixture(spec, result))
            continue

        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            warnings.append(
                f"generator produced non-JSON output for {spec.case_id}: {e}"
            )
            save_json(
                target_path,
                _make_sentinel_fixture(spec, None, error_msg=str(e)),
            )
            continue

        pii_warnings = detect_pii_shaped_strings(parsed.get("input", {}))
        for w in pii_warnings:
            warnings.append(f"{spec.case_id}: {w}")

        prompt = render_generator_prompt(spec, rules_dir=rules_dir)
        record = FixtureRecord(
            case_id=spec.case_id,
            slice=spec.slice,
            track=spec.track,
            target_rule_id=spec.target_rule_id,
            probe_intent=spec.probe_intent,
            generated_by=f"claude-batch/{GENERATOR_MODEL}",
            generated_at=_now_iso(),
            generator_prompt_hash=sha256_of_text(prompt),
            flavor_hint=parsed.get("flavor_hint"),
            input=parsed.get("input", {}),
            expected=parsed.get("expected", {}),
        )
        save_json(target_path, record.to_dict())
        new_count += 1

    return new_count, skip_count, warnings


def batch_judge(
    cases_to_judge: list[tuple[FixtureRecord, EvalRecord]],
    *,
    cache_dir: Path,
    client: anthropic.Anthropic | None = None,
) -> dict[str, JudgeRecord]:
    """Submit all judge prompts as one batch, poll, parse, write cache entries.

    Returns {case_id: JudgeRecord}. Only processes cases passed in — the
    caller is responsible for cache-hit checks. This function writes to
    cache_dir but does not read from it (idempotent within one run).
    """
    if client is None:
        client = anthropic.Anthropic()

    cache_dir.mkdir(parents=True, exist_ok=True)

    if not cases_to_judge:
        return {}

    requests = [
        _build_judge_request(fixture, eval_record)
        for fixture, eval_record in cases_to_judge
    ]
    case_by_custom_id = {
        f"judge-{fixture.case_id}": (fixture, eval_record)
        for fixture, eval_record in cases_to_judge
    }

    rubric_version = _rubric_version()

    message_batch = client.messages.batches.create(requests=requests)
    _poll_until_ended(client, message_batch.id)

    out: dict[str, JudgeRecord] = {}
    for result in client.messages.batches.results(message_batch.id):
        pair = case_by_custom_id.get(result.custom_id)
        if pair is None:
            continue
        fixture, eval_record = pair
        findings_hash = sha256_of_obj(eval_record.findings)
        prompt = render_judge_prompt(fixture, eval_record)
        prompt_hash = sha256_of_text(prompt)
        cache_key = compute_judge_cache_key(
            eval_record.input_hash, findings_hash, rubric_version, prompt_hash
        )
        cached_path = cache_dir / f"{cache_key}.json"
        cache_key_inputs = {
            "case_id": fixture.case_id,
            "input_hash": eval_record.input_hash,
            "findings_hash": findings_hash,
            "rubric_version": rubric_version,
            "judge_prompt_hash": prompt_hash,
        }

        if result.result.type != "succeeded":
            record = JudgeRecord(
                cache_key=cache_key,
                cache_key_inputs=cache_key_inputs,
                case_id=fixture.case_id,
                judged_at=_now_iso(),
                judged_by=f"claude-batch/{JUDGE_MODEL}",
                verdict="unrunnable",
                subscores={},
                flags=[f"judge_error:{result.result.type}"],
                raw_judge_output=str(getattr(result.result, "error", "")),
            )
        else:
            msg = result.result.message
            text = next((b.text for b in msg.content if b.type == "text"), "")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                record = JudgeRecord(
                    cache_key=cache_key,
                    cache_key_inputs=cache_key_inputs,
                    case_id=fixture.case_id,
                    judged_at=_now_iso(),
                    judged_by=f"claude-batch/{JUDGE_MODEL}",
                    verdict="unrunnable",
                    subscores={},
                    flags=[f"judge_parse_error:{e}"],
                    raw_judge_output=text[:500],
                )
            else:
                record = JudgeRecord(
                    cache_key=cache_key,
                    cache_key_inputs=cache_key_inputs,
                    case_id=fixture.case_id,
                    judged_at=_now_iso(),
                    judged_by=f"claude-batch/{JUDGE_MODEL}",
                    verdict=parsed.get("verdict", "unrunnable"),
                    subscores=parsed.get("subscores", {}),
                    flags=parsed.get("flags", []),
                    raw_judge_output=text,
                )

        save_json(cached_path, record.to_dict())
        out[fixture.case_id] = record

    return out
