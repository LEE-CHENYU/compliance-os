"""Manifest-backed loop runner for data-room batch iteration."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "config" / "data_room_batches.yaml"
DEFAULT_LOG_ROOT = PROJECT_ROOT / "logs" / "data-room-batch-loop"


@dataclass(slots=True)
class BatchHookSpec:
    name: str
    command: str
    timeout_sec: int | None = None
    retries: int = 0
    retry_delay_sec: float = 0.0


@dataclass(slots=True)
class BatchSpec:
    batch_id: str
    batch_number: int
    focus: str
    status: str
    record: str | None = None
    source_scope: list[str] = field(default_factory=list)
    target_size: int | None = None
    validation_hooks: list[BatchHookSpec] = field(default_factory=list)


@dataclass(slots=True)
class HookAttemptResult:
    attempt_number: int
    passed: bool
    exit_code: int
    output: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "output": self.output,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "timed_out": self.timed_out,
        }


@dataclass(slots=True)
class HookResult:
    name: str
    command: str
    passed: bool
    exit_code: int
    output: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    attempt_count: int = 1
    timed_out: bool = False
    attempts: list[HookAttemptResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "output": self.output,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attempt_count": self.attempt_count,
            "timed_out": self.timed_out,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


@dataclass(slots=True)
class BatchState:
    spec: BatchSpec
    resolved: bool
    unresolved_issues: list[str]
    record_exists: bool
    validation_results: list[HookResult] = field(default_factory=list)
    validation_ran: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.spec.batch_id,
            "batch_number": self.spec.batch_number,
            "focus": self.spec.focus,
            "status": self.spec.status,
            "record": self.spec.record,
            "source_scope": self.spec.source_scope,
            "target_size": self.spec.target_size,
            "resolved": self.resolved,
            "record_exists": self.record_exists,
            "unresolved_issues": self.unresolved_issues,
            "validation_ran": self.validation_ran,
            "validation_results": [result.to_dict() for result in self.validation_results],
        }


def load_manifest(manifest_path: str | Path = DEFAULT_MANIFEST_PATH) -> tuple[str | None, list[BatchSpec]]:
    path = Path(manifest_path)
    data = yaml.safe_load(path.read_text()) or {}
    batches = []
    for item in data.get("batches", []):
        validation_hooks: list[BatchHookSpec] = []
        for index, hook in enumerate(item.get("validation_hooks") or []):
            if isinstance(hook, str):
                validation_hooks.append(
                    BatchHookSpec(name=f"hook_{index + 1}", command=hook)
                )
                continue
            validation_hooks.append(
                BatchHookSpec(
                    name=str(hook.get("name") or f"hook_{index + 1}"),
                    command=str(hook["command"]),
                    timeout_sec=(
                        int(hook["timeout_sec"])
                        if hook.get("timeout_sec") is not None
                        else None
                    ),
                    retries=max(int(hook.get("retries", 0)), 0),
                    retry_delay_sec=max(float(hook.get("retry_delay_sec", 0.0)), 0.0),
                )
            )
        batches.append(
            BatchSpec(
                batch_id=str(item["id"]),
                batch_number=int(item["number"]),
                focus=str(item["focus"]),
                status=str(item.get("status", "planned")),
                record=item.get("record"),
                source_scope=list(item.get("source_scope") or []),
                target_size=item.get("target_size"),
                validation_hooks=validation_hooks,
            )
        )
    batches.sort(key=lambda batch: batch.batch_number)
    return data.get("source_root"), batches


def select_round(batches: list[BatchSpec], round_size: int) -> list[BatchSpec]:
    return batches[: max(round_size, 0)]


def select_batches(
    batches: list[BatchSpec],
    *,
    round_size: int,
    batch_ids: list[str] | None = None,
    batch_numbers: list[int] | None = None,
) -> list[BatchSpec]:
    selected = batches
    if batch_ids:
        wanted_ids = {value.strip() for value in batch_ids}
        selected = [batch for batch in selected if batch.batch_id in wanted_ids]
    if batch_numbers:
        wanted_numbers = set(batch_numbers)
        selected = [batch for batch in selected if batch.batch_number in wanted_numbers]
    if batch_ids or batch_numbers:
        return selected
    return select_round(selected, round_size)


def parse_remaining_gaps(record_path: str | Path) -> list[str]:
    text = Path(record_path).read_text()
    lines = text.splitlines()

    in_section = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower() == "## remaining gaps":
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section:
            continue
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
            continue
        if stripped[:2].isdigit() and ". " in stripped:
            items.append(stripped.split(". ", 1)[1].strip())
            continue
        if stripped and stripped[0].isdigit() and ". " in stripped:
            items.append(stripped.split(". ", 1)[1].strip())
    return items


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _command_template_context(
    *,
    project_root: Path,
    source_root: str | None,
    spec: BatchSpec,
) -> dict[str, str]:
    record = spec.record or ""
    source_root_str = source_root or ""
    context = {
        "batch_id": spec.batch_id,
        "batch_number": f"{spec.batch_number:02d}",
        "focus": spec.focus,
        "status": spec.status,
        "record": record,
        "source_root": source_root_str,
        "project_root": str(project_root),
        "python": sys.executable,
    }
    context.update({f"{key}_quoted": shlex.quote(value) for key, value in context.items()})
    return context


def _run_shell_command(
    command_template: str,
    *,
    project_root: Path,
    source_root: str | None,
    spec: BatchSpec,
    timeout_sec: int | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = command_template.format(
        **_command_template_context(
            project_root=project_root,
            source_root=source_root,
            spec=spec,
        )
    )
    return subprocess.run(
        command,
        shell=True,
        cwd=project_root,
        check=False,
        text=True,
        capture_output=capture_output,
        timeout=timeout_sec,
    )


def _execute_command_attempt(
    expanded_command: str,
    *,
    project_root: Path,
    timeout_sec: int | None = None,
    attempt_number: int = 1,
) -> HookAttemptResult:
    started_at = _utc_now_iso()
    try:
        completed = subprocess.run(
            expanded_command,
            shell=True,
            cwd=project_root,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        output_parts = [
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        ]
        output = "\n".join(output_parts) or None
        return HookAttemptResult(
            attempt_number=attempt_number,
            passed=completed.returncode == 0,
            exit_code=completed.returncode,
            output=output,
            started_at=started_at,
            finished_at=_utc_now_iso(),
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        return HookAttemptResult(
            attempt_number=attempt_number,
            passed=False,
            exit_code=124,
            output=f"Timed out after {timeout_sec}s",
            started_at=started_at,
            finished_at=_utc_now_iso(),
            timed_out=True,
        )


def _execute_command_result(
    name: str,
    command_template: str,
    *,
    project_root: Path,
    source_root: str | None,
    spec: BatchSpec,
    timeout_sec: int | None = None,
    retries: int = 0,
    retry_delay_sec: float = 0.0,
) -> HookResult:
    expanded_command = command_template.format(
        **_command_template_context(
            project_root=project_root,
            source_root=source_root,
            spec=spec,
        )
    )
    attempts: list[HookAttemptResult] = []
    total_attempts = max(retries, 0) + 1

    for attempt_number in range(1, total_attempts + 1):
        attempt = _execute_command_attempt(
            expanded_command,
            project_root=project_root,
            timeout_sec=timeout_sec,
            attempt_number=attempt_number,
        )
        attempts.append(attempt)
        if attempt.passed:
            break
        if attempt_number < total_attempts and retry_delay_sec > 0:
            time.sleep(retry_delay_sec)

    final_attempt = attempts[-1]
    return HookResult(
        name=name,
        command=expanded_command,
        passed=final_attempt.passed,
        exit_code=final_attempt.exit_code,
        output=final_attempt.output,
        started_at=attempts[0].started_at,
        finished_at=final_attempt.finished_at,
        attempt_count=len(attempts),
        timed_out=final_attempt.timed_out,
        attempts=attempts,
    )


def run_validation_hooks(
    project_root: str | Path,
    spec: BatchSpec,
    *,
    source_root: str | None = None,
    extra_validation_commands: list[str] | None = None,
    timeout_sec: int = 600,
) -> list[HookResult]:
    root = Path(project_root)
    hooks = list(spec.validation_hooks)
    for index, command in enumerate(extra_validation_commands or [], start=1):
        hooks.append(BatchHookSpec(name=f"cli_validation_{index}", command=command))

    results: list[HookResult] = []
    for hook in hooks:
        results.append(
            _execute_command_result(
                hook.name,
                hook.command,
                project_root=root,
                source_root=source_root,
                spec=spec,
                timeout_sec=hook.timeout_sec if hook.timeout_sec is not None else timeout_sec,
                retries=hook.retries,
                retry_delay_sec=hook.retry_delay_sec,
            )
        )
    return results


def assess_batch(
    project_root: str | Path,
    spec: BatchSpec,
    *,
    source_root: str | None = None,
    run_validation_hooks_flag: bool = False,
    extra_validation_commands: list[str] | None = None,
    validation_timeout_sec: int = 600,
    require_validation_evidence: bool = False,
) -> BatchState:
    root = Path(project_root)
    unresolved_issues: list[str] = []
    record_exists = False
    validation_results: list[HookResult] = []

    if spec.status.lower() not in {"completed", "resolved"}:
        unresolved_issues.append(f"Batch status is {spec.status}")

    if spec.record:
        record_path = root / spec.record
        record_exists = record_path.exists()
        if record_exists:
            unresolved_issues.extend(parse_remaining_gaps(record_path))
        else:
            unresolved_issues.append(f"Record file missing: {spec.record}")
    else:
        unresolved_issues.append("No record file defined")

    if run_validation_hooks_flag:
        validation_results = run_validation_hooks(
            root,
            spec,
            source_root=source_root,
            extra_validation_commands=extra_validation_commands,
            timeout_sec=validation_timeout_sec,
        )
        if require_validation_evidence and not validation_results:
            unresolved_issues.append("No validation hooks configured for batch")
        for result in validation_results:
            if not result.passed:
                unresolved_issues.append(f"Validation hook failed: {result.name}")

    return BatchState(
        spec=spec,
        resolved=not unresolved_issues,
        unresolved_issues=unresolved_issues,
        record_exists=record_exists,
        validation_results=validation_results,
        validation_ran=run_validation_hooks_flag,
    )


def _run_batch_command(
    template: str,
    *,
    project_root: Path,
    source_root: str | None,
    state: BatchState,
) -> HookResult:
    return _execute_command_result(
        "batch_run",
        template,
        project_root=project_root,
        source_root=source_root,
        spec=state.spec,
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


def _create_session_log_dir(log_root: str | Path) -> Path:
    root = Path(log_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = 0
    while True:
        session_dir = root / stamp if suffix == 0 else root / f"{stamp}-{suffix:02d}"
        try:
            session_dir.mkdir(parents=True, exist_ok=False)
            return session_dir
        except FileExistsError:
            suffix += 1


def _blocked_batch_state(state: BatchState, *, blocking_batch_id: str) -> BatchState:
    blocked_issue = f"Blocked by unresolved prior batch: {blocking_batch_id}"
    unresolved_issues = list(state.unresolved_issues)
    if blocked_issue not in unresolved_issues:
        unresolved_issues.append(blocked_issue)
    return BatchState(
        spec=state.spec,
        resolved=False,
        unresolved_issues=unresolved_issues,
        record_exists=state.record_exists,
        validation_results=state.validation_results,
        validation_ran=state.validation_ran,
    )


def execute_loop(
    project_root: str | Path,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    round_size: int = 5,
    max_passes: int = 5,
    run_command: str | None = None,
    batch_ids: list[str] | None = None,
    batch_numbers: list[int] | None = None,
    run_validation_hooks_flag: bool = False,
    extra_validation_commands: list[str] | None = None,
    validation_timeout_sec: int = 600,
    session_log_dir: str | Path | None = None,
) -> tuple[list[BatchState], int]:
    root = Path(project_root)
    source_root, batches = load_manifest(manifest_path)
    selected = select_batches(
        batches,
        round_size=round_size,
        batch_ids=batch_ids,
        batch_numbers=batch_numbers,
    )
    validation_enabled = run_validation_hooks_flag or bool(extra_validation_commands)
    require_validation_evidence = run_command is not None
    if run_command and not validation_enabled:
        raise ValueError("run_command mode requires validation hooks or validate commands")

    session_dir = Path(session_log_dir) if session_log_dir else None
    events_path = session_dir / "events.jsonl" if session_dir else None
    session_payload = {
        "started_at": _utc_now_iso(),
        "manifest_path": str(Path(manifest_path)),
        "source_root": source_root,
        "round_size": round_size,
        "max_passes_per_batch": max_passes,
        "run_command": run_command,
        "run_validation_hooks": run_validation_hooks_flag,
        "extra_validation_commands": extra_validation_commands or [],
        "selected_batches": [batch.batch_id for batch in selected],
    }
    if session_dir:
        _write_json(session_dir / "session.json", session_payload)

    if not run_command:
        states = [
            assess_batch(
                root,
                batch,
                source_root=source_root,
                run_validation_hooks_flag=run_validation_hooks_flag,
                extra_validation_commands=extra_validation_commands,
                validation_timeout_sec=validation_timeout_sec,
                require_validation_evidence=require_validation_evidence,
            )
            for batch in selected
        ]
        if session_dir and events_path:
            for state in states:
                batch_dir = session_dir / "batches" / f"batch_{state.spec.batch_number:02d}"
                _write_json(batch_dir / "assessment.json", state.to_dict())
                _append_jsonl(
                    events_path,
                    {
                        "timestamp": _utc_now_iso(),
                        "type": "assessment",
                        "batch_id": state.spec.batch_id,
                        "batch_number": state.spec.batch_number,
                        "resolved": state.resolved,
                        "validation_ran": state.validation_ran,
                        "issues": state.unresolved_issues,
                    },
                )
            session_payload.update(
                {
                    "completed_at": _utc_now_iso(),
                    "passes_executed": 0,
                    "resolved_batches": [state.spec.batch_id for state in states if state.resolved],
                    "unresolved_batches": [state.spec.batch_id for state in states if not state.resolved],
                }
            )
            _write_json(session_dir / "session.json", session_payload)
            _append_jsonl(
                events_path,
                {
                    "timestamp": _utc_now_iso(),
                    "type": "session_complete",
                    "passes_executed": 0,
                    "resolved_batches": session_payload["resolved_batches"],
                    "unresolved_batches": session_payload["unresolved_batches"],
                },
            )
        return states, 0

    states: list[BatchState] = []
    passes = 0
    for index, batch in enumerate(selected):
        state = assess_batch(
            root,
            batch,
            source_root=source_root,
            run_validation_hooks_flag=run_validation_hooks_flag,
            extra_validation_commands=extra_validation_commands,
            validation_timeout_sec=validation_timeout_sec,
            require_validation_evidence=require_validation_evidence,
        )
        if session_dir and events_path:
            batch_dir = session_dir / "batches" / f"batch_{batch.batch_number:02d}"
            _write_json(batch_dir / "assessment_initial.json", state.to_dict())
            _append_jsonl(
                events_path,
                {
                    "timestamp": _utc_now_iso(),
                    "type": "batch_start",
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "resolved": state.resolved,
                    "issues": state.unresolved_issues,
                },
            )

        if state.resolved:
            states.append(state)
            if session_dir and events_path:
                batch_dir = session_dir / "batches" / f"batch_{batch.batch_number:02d}"
                _write_json(batch_dir / "final_state.json", state.to_dict())
                _append_jsonl(
                    events_path,
                    {
                        "timestamp": _utc_now_iso(),
                        "type": "batch_complete",
                        "batch_id": batch.batch_id,
                        "batch_number": batch.batch_number,
                        "resolved": state.resolved,
                        "attempts_executed": 0,
                        "issues": state.unresolved_issues,
                    },
                )
            continue

        batch_passes = 0
        while batch_passes < max_passes and not state.resolved:
            batch_passes += 1
            passes += 1
            before_issue_count = len(state.unresolved_issues)
            pre_state = state
            run_result = _run_batch_command(
                run_command,
                project_root=root,
                source_root=source_root,
                state=state,
            )
            refreshed = assess_batch(
                root,
                state.spec,
                source_root=source_root,
                run_validation_hooks_flag=run_validation_hooks_flag,
                extra_validation_commands=extra_validation_commands,
                validation_timeout_sec=validation_timeout_sec,
                require_validation_evidence=require_validation_evidence,
            )
            state = refreshed
            if session_dir and events_path:
                batch_dir = session_dir / "batches" / f"batch_{batch.batch_number:02d}"
                attempt_payload = {
                    "timestamp": _utc_now_iso(),
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "attempt": batch_passes,
                    "pre_state": pre_state.to_dict(),
                    "run_result": run_result.to_dict(),
                    "post_state": state.to_dict(),
                }
                _write_json(batch_dir / f"attempt_{batch_passes:02d}.json", attempt_payload)
                _append_jsonl(
                    events_path,
                    {
                        "timestamp": _utc_now_iso(),
                        "type": "batch_attempt",
                        "batch_id": batch.batch_id,
                        "batch_number": batch.batch_number,
                        "attempt": batch_passes,
                        "run_exit_code": run_result.exit_code,
                        "resolved_after_attempt": state.resolved,
                        "issues_after_attempt": state.unresolved_issues,
                    },
                )
            if state.resolved:
                break
            if len(state.unresolved_issues) < before_issue_count:
                continue

        states.append(state)
        if session_dir and events_path:
            batch_dir = session_dir / "batches" / f"batch_{batch.batch_number:02d}"
            _write_json(batch_dir / "final_state.json", state.to_dict())
            _append_jsonl(
                events_path,
                {
                    "timestamp": _utc_now_iso(),
                    "type": "batch_complete",
                    "batch_id": batch.batch_id,
                    "batch_number": batch.batch_number,
                    "resolved": state.resolved,
                    "attempts_executed": batch_passes,
                    "issues": state.unresolved_issues,
                },
            )

        if not state.resolved:
            for remaining in selected[index + 1:]:
                remaining_state = assess_batch(
                    root,
                    remaining,
                    source_root=source_root,
                    run_validation_hooks_flag=False,
                    extra_validation_commands=extra_validation_commands,
                    validation_timeout_sec=validation_timeout_sec,
                    require_validation_evidence=False,
                )
                remaining_state = _blocked_batch_state(
                    remaining_state,
                    blocking_batch_id=batch.batch_id,
                )
                states.append(remaining_state)
                if session_dir and events_path:
                    batch_dir = session_dir / "batches" / f"batch_{remaining.batch_number:02d}"
                    _write_json(batch_dir / "skipped_state.json", remaining_state.to_dict())
                    _append_jsonl(
                        events_path,
                        {
                            "timestamp": _utc_now_iso(),
                            "type": "batch_skipped_after_failure",
                            "batch_id": remaining.batch_id,
                            "batch_number": remaining.batch_number,
                            "blocked_by_batch": batch.batch_id,
                            "issues": remaining_state.unresolved_issues,
                        },
                    )
            break

    if session_dir and events_path:
        session_payload.update(
            {
                "completed_at": _utc_now_iso(),
                "passes_executed": passes,
                "resolved_batches": [state.spec.batch_id for state in states if state.resolved],
                "unresolved_batches": [state.spec.batch_id for state in states if not state.resolved],
            }
        )
        _write_json(session_dir / "session.json", session_payload)
        _append_jsonl(
            events_path,
            {
                "timestamp": _utc_now_iso(),
                "type": "session_complete",
                "passes_executed": passes,
                "resolved_batches": session_payload["resolved_batches"],
                "unresolved_batches": session_payload["unresolved_batches"],
            },
        )

    return states, passes


def _render_run_mode_description(run_command: str | None, run_validation_hooks_flag: bool) -> str:
    if not run_command:
        return "assessment_only"
    if run_validation_hooks_flag:
        return "sequential_run_then_validate"
    return "sequential_run"


def render_summary(
    states: list[BatchState],
    *,
    total_batches: int,
    round_size: int,
    pass_count: int = 0,
    run_command: str | None = None,
    run_validation_hooks_flag: bool = False,
    session_log_dir: str | Path | None = None,
) -> str:
    lines = [
        f"Total batches defined: {total_batches}",
        f"First-round batch cap: {round_size}",
        f"Run mode: {_render_run_mode_description(run_command, run_validation_hooks_flag)}",
        f"Batch iterations executed: {pass_count}",
    ]
    if session_log_dir:
        lines.append(f"Session log dir: {session_log_dir}")
    lines.extend(["", "Selected batches:"])
    for state in states:
        lines.append(
            f"- Batch {state.spec.batch_number:02d} [{state.spec.status}] "
            f"resolved={str(state.resolved).lower()} "
            f"issues={len(state.unresolved_issues)} "
            f"focus={state.spec.focus}"
        )
        if state.spec.record:
            lines.append(f"  record: {state.spec.record}")
        if state.validation_ran:
            total_hooks = len(state.validation_results)
            passed_hooks = sum(1 for result in state.validation_results if result.passed)
            if total_hooks:
                lines.append(f"  validation: {passed_hooks}/{total_hooks} passed")
            else:
                lines.append("  validation: no hooks configured")
            failed_hook = next((result for result in state.validation_results if not result.passed), None)
            if failed_hook is not None:
                lines.append(f"  failed hook: {failed_hook.name}")
        if state.unresolved_issues:
            lines.append(f"  next issue: {state.unresolved_issues[0]}")
    unresolved = [state for state in states if not state.resolved]
    lines.extend(
        [
            "",
            f"Resolved in selection: {len(states) - len(unresolved)}",
            f"Still unresolved: {len(unresolved)}",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Iterate through data-room batches until recorded issues are cleared.",
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to the batch manifest YAML.",
    )
    parser.add_argument(
        "--round-size",
        type=int,
        default=5,
        help="How many batches to include in the first round.",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=5,
        help="Maximum processing iterations per batch when --run-command is provided.",
    )
    parser.add_argument(
        "--batch-id",
        action="append",
        default=[],
        help="Restrict execution to a specific batch id. May be repeated.",
    )
    parser.add_argument(
        "--batch-number",
        type=int,
        action="append",
        default=[],
        help="Restrict execution to a specific batch number. May be repeated.",
    )
    parser.add_argument(
        "--run-command",
        default=None,
        help=(
            "Optional shell command template to run for each unresolved batch. "
            "Placeholders: {batch_id}, {batch_number}, {focus}, {status}, {record}, {source_root}, "
            "{project_root}, {python}, and *_quoted variants."
        ),
    )
    parser.add_argument(
        "--run-validation-hooks",
        action="store_true",
        help="Run manifest-defined validation hooks for each selected batch.",
    )
    parser.add_argument(
        "--validate-command",
        action="append",
        default=[],
        help=(
            "Additional validation command template to run for each selected batch. "
            "Supports the same placeholders as --run-command."
        ),
    )
    parser.add_argument(
        "--validation-timeout-sec",
        type=int,
        default=600,
        help="Timeout per validation hook command.",
    )
    parser.add_argument(
        "--log-root",
        default=str(DEFAULT_LOG_ROOT),
        help="Root directory for timestamped session logs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the selected round summary as JSON.",
    )
    parser.add_argument(
        "--fail-on-unresolved",
        action="store_true",
        help="Exit non-zero if any selected batch remains unresolved.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    source_root, batches = load_manifest(args.manifest)
    session_log_dir = _create_session_log_dir(args.log_root)
    states, passes = execute_loop(
        PROJECT_ROOT,
        manifest_path=args.manifest,
        round_size=args.round_size,
        max_passes=args.max_passes,
        run_command=args.run_command,
        batch_ids=args.batch_id,
        batch_numbers=args.batch_number,
        run_validation_hooks_flag=args.run_validation_hooks,
        extra_validation_commands=args.validate_command,
        validation_timeout_sec=args.validation_timeout_sec,
        session_log_dir=session_log_dir,
    )

    if args.json:
        payload = {
            "manifest": str(Path(args.manifest)),
            "source_root": source_root,
            "total_batches": len(batches),
            "round_size": args.round_size,
            "passes_executed": passes,
            "session_log_dir": str(session_log_dir),
            "selected_batches": [state.to_dict() for state in states],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(
            render_summary(
                states,
                total_batches=len(batches),
                round_size=args.round_size,
                pass_count=passes,
                run_command=args.run_command,
                run_validation_hooks_flag=args.run_validation_hooks,
                session_log_dir=session_log_dir,
            )
        )

    if args.fail_on_unresolved and any(not state.resolved for state in states):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
