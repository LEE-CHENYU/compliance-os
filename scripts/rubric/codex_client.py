"""Thin wrapper around `codex exec` for structured-JSON LLM calls.

Hermetic: every call runs in a scratch workspace with --sandbox read-only,
--ephemeral, and --skip-git-repo-check. The agent cannot read files or run
shell commands. All knowledge must be in the prompt.

Defaults match the "not a coding task" policy: gpt-5.4 / xhigh, not
gpt-5.3-codex. See docs/superpowers/specs/2026-04-10-rubric-loop-design.md
decision D8 for rationale.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from rubric.models import CodexCallError, CodexCallResult

SCRATCH_WORKSPACE = Path("/tmp/rubric-loop-workspace")

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_FALLBACK_MODEL = "gpt-5.4-mini"
DEFAULT_REASONING_EFFORT = "xhigh"

MODEL = os.environ.get("RUBRIC_CODEX_MODEL", DEFAULT_MODEL)
FALLBACK_MODEL = os.environ.get("RUBRIC_CODEX_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
REASONING_EFFORT = os.environ.get("RUBRIC_CODEX_REASONING", DEFAULT_REASONING_EFFORT)


def call_codex(
    *,
    prompt: str,
    schema_path: Path,
    model: str = MODEL,
    reasoning_effort: str = REASONING_EFFORT,
    timeout_s: int = 180,
    max_retries: int = 2,
    fallback_model: str | None = FALLBACK_MODEL,
) -> CodexCallResult:
    """Invoke `codex exec` with structured output, retries, and fallback.

    Retries only the retryable failure kinds (timeout, parse_failure,
    schema_violation). Subprocess failures fail fast except for
    "model is not supported" which triggers a one-shot fallback.
    """
    SCRATCH_WORKSPACE.mkdir(parents=True, exist_ok=True)
    last_error: CodexCallError | None = None

    for attempt in range(1, max_retries + 2):  # initial + retries
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as tmp:
            output_path = Path(tmp.name)

        try:
            # Note: --output-schema is intentionally NOT passed. OpenAI's
            # structured-output mode requires `additionalProperties: false` on
            # every nested object, which conflicts with our dynamic-field
            # design (answers/extraction_*/comparisons are open-ended dicts
            # keyed by field name). We rely on (1) the prompt telling the
            # model to match the schema and (2) local `jsonschema` validation
            # below, with retries on violation, to enforce the contract.
            cmd = [
                "codex", "exec",
                "-c", f'model_reasoning_effort="{reasoning_effort}"',
                "--model", model,
                "--sandbox", "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "--output-last-message", str(output_path),
                "--json",
                "--cd", str(SCRATCH_WORKSPACE),
                "-",
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=timeout_s,
                )
            except subprocess.TimeoutExpired:
                last_error = CodexCallError(
                    kind="timeout",
                    message=f"codex exec timed out after {timeout_s}s",
                    attempts=attempt,
                )
                continue

            if proc.returncode != 0:
                combined = (proc.stdout or "") + (proc.stderr or "")
                if (
                    fallback_model
                    and fallback_model != model
                    and "model is not supported" in combined.lower()
                ):
                    return call_codex(
                        prompt=prompt,
                        schema_path=schema_path,
                        model=fallback_model,
                        reasoning_effort=reasoning_effort,
                        timeout_s=timeout_s,
                        max_retries=max_retries,
                        fallback_model=None,  # prevent recursion
                    )
                raise CodexCallError(
                    kind="subprocess_failure",
                    message=f"codex exec returned {proc.returncode}",
                    stderr=combined,
                    attempts=attempt,
                )

            raw = output_path.read_text().strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                last_error = CodexCallError(
                    kind="parse_failure",
                    message=f"output was not valid JSON: {e}",
                    stderr=raw[:500],
                    attempts=attempt,
                )
                continue

            schema = json.loads(schema_path.read_text())
            validator = Draft202012Validator(schema)
            try:
                validator.validate(parsed)
            except ValidationError as e:
                last_error = CodexCallError(
                    kind="schema_violation",
                    message=f"output violates schema: {e.message}",
                    stderr=raw[:500],
                    attempts=attempt,
                )
                continue

            events = [
                json.loads(line)
                for line in (proc.stdout or "").splitlines()
                if line.strip()
            ]
            tokens_in, tokens_out = _extract_token_counts(events)

            return CodexCallResult(
                text=raw,
                parsed=parsed,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=0,    # parsed from events in a follow-up pass; OK to 0-init
                raw_events=events,
                attempts=attempt,
            )
        finally:
            output_path.unlink(missing_ok=True)

    assert last_error is not None
    raise last_error


def _extract_token_counts(events: list[dict]) -> tuple[int | None, int | None]:
    """Find the last usage event and extract token counts.

    The codex JSONL event schema may evolve; we fail soft (return None) if the
    event isn't present rather than crashing the whole run.
    """
    for event in reversed(events):
        if isinstance(event, dict) and event.get("type") == "usage":
            return event.get("input_tokens"), event.get("output_tokens")
    return None, None
