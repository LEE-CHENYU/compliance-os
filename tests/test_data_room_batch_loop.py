import json
from datetime import datetime as real_datetime
from datetime import timezone

import pytest

import compliance_os.batch_loop as batch_loop
from compliance_os.batch_loop import (
    BatchHookSpec,
    BatchSpec,
    _create_session_log_dir,
    assess_batch,
    execute_loop,
    load_manifest,
    parse_remaining_gaps,
    select_batches,
    select_round,
)


def test_parse_remaining_gaps_reads_numbered_and_bulleted_items(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "## Remaining gaps",
                "",
                "1. First issue",
                "- Second issue",
                "* Third issue",
                "",
                "## Next queue",
                "1. Later item",
            ]
        )
    )

    assert parse_remaining_gaps(record) == [
        "First issue",
        "Second issue",
        "Third issue",
    ]


def test_parse_remaining_gaps_reads_current_batch_blockers_and_ignores_deferred_backlog(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "## Current batch blockers",
                "",
                "1. First blocker",
                "- Second blocker",
                "",
                "## Deferred backlog",
                "1. Platform item",
                "2. Later batch item",
            ]
        )
    )

    assert parse_remaining_gaps(record) == [
        "First blocker",
        "Second blocker",
    ]


def test_assess_batch_requires_completed_status_and_no_remaining_gaps(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "## Remaining gaps",
                "",
                "1. Still broken",
            ]
        )
    )
    spec = BatchSpec(
        batch_id="batch_01",
        batch_number=1,
        focus="Focus",
        status="completed",
        record=str(record.relative_to(tmp_path)),
    )

    state = assess_batch(tmp_path, spec)

    assert state.resolved is False
    assert state.record_exists is True
    assert state.unresolved_issues == ["Still broken"]


def test_assess_batch_marks_planned_batch_unresolved_even_without_gaps(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text("# Batch\n\n## Remaining gaps\n")
    spec = BatchSpec(
        batch_id="batch_04",
        batch_number=4,
        focus="Planned",
        status="planned",
        record=str(record.relative_to(tmp_path)),
    )

    state = assess_batch(tmp_path, spec)

    assert state.resolved is False
    assert state.unresolved_issues == ["Batch status is planned"]


def test_assess_batch_marks_failed_validation_hook_unresolved(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text("# Batch\n\n## Remaining gaps\n")
    spec = BatchSpec(
        batch_id="batch_02",
        batch_number=2,
        focus="Validated",
        status="completed",
        record=str(record.relative_to(tmp_path)),
        validation_hooks=[
            BatchHookSpec(
                name="failing_hook",
                command='{python_quoted} -c "import sys; sys.exit(2)"',
            )
        ],
    )

    state = assess_batch(
        tmp_path,
        spec,
        run_validation_hooks_flag=True,
        validation_timeout_sec=10,
    )

    assert state.resolved is False
    assert state.validation_ran is True
    assert len(state.validation_results) == 1
    assert state.validation_results[0].passed is False
    assert state.unresolved_issues == ["Validation hook failed: failing_hook"]


def test_assess_batch_retries_hook_and_recovers_from_transient_failure(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text("# Batch\n\n## Remaining gaps\n")
    spec = BatchSpec(
        batch_id="batch_02",
        batch_number=2,
        focus="Validated",
        status="completed",
        record=str(record.relative_to(tmp_path)),
        validation_hooks=[
            BatchHookSpec(
                name="transient_hook",
                command=(
                    "count_file={project_root_quoted}/counter.txt; "
                    "count=$(cat \"$count_file\" 2>/dev/null || echo 0); "
                    "count=$((count+1)); "
                    "printf '%s' \"$count\" > \"$count_file\"; "
                    "test \"$count\" -ge 2"
                ),
                retries=1,
            )
        ],
    )

    state = assess_batch(
        tmp_path,
        spec,
        run_validation_hooks_flag=True,
        validation_timeout_sec=10,
    )

    assert state.resolved is True
    assert state.validation_results[0].passed is True
    assert state.validation_results[0].attempt_count == 2
    assert len(state.validation_results[0].attempts) == 2
    assert state.validation_results[0].attempts[0].passed is False
    assert state.validation_results[0].attempts[1].passed is True


def test_load_manifest_parses_validation_hooks():
    _source_root, batches = load_manifest()

    batch_01 = next(batch for batch in batches if batch.batch_id == "batch_01")

    assert batch_01.validation_hooks
    assert batch_01.validation_hooks[0].name == "batch_01_focused_tests"
    assert "{python_quoted}" in batch_01.validation_hooks[0].command
    assert batch_01.validation_hooks[0].retries == 1


def test_create_session_log_dir_handles_timestamp_collision(tmp_path, monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(batch_loop, "datetime", FixedDateTime)

    first = _create_session_log_dir(tmp_path / "logs")
    second = _create_session_log_dir(tmp_path / "logs")

    assert first.name == "20260101T000000Z"
    assert second.name == "20260101T000000Z-01"


def test_select_round_limits_to_requested_batch_count():
    batches = [
        BatchSpec(batch_id=f"batch_{index:02d}", batch_number=index, focus="x", status="planned")
        for index in range(1, 7)
    ]

    selected = select_round(batches, 5)

    assert [batch.batch_number for batch in selected] == [1, 2, 3, 4, 5]


def test_select_batches_can_target_specific_batch_numbers():
    batches = [
        BatchSpec(batch_id=f"batch_{index:02d}", batch_number=index, focus="x", status="planned")
        for index in range(1, 7)
    ]

    selected = select_batches(batches, round_size=5, batch_numbers=[3, 5])

    assert [batch.batch_number for batch in selected] == [3, 5]


def test_execute_loop_runs_batches_sequentially_until_validation_passes(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "batch-01.md").write_text("# Batch 01\n\n## Remaining gaps\n")
    (tmp_path / "docs" / "batch-02.md").write_text("# Batch 02\n\n## Remaining gaps\n")
    manifest.write_text(
        "\n".join(
            [
                f"source_root: {tmp_path}",
                "batches:",
                "  - id: batch_01",
                "    number: 1",
                "    focus: first",
                "    status: completed",
                "    record: docs/batch-01.md",
                "    validation_hooks:",
                "      - name: hook_01",
                "        command: test -f {project_root_quoted}/validated_01",
                "  - id: batch_02",
                "    number: 2",
                "    focus: second",
                "    status: completed",
                "    record: docs/batch-02.md",
                "    validation_hooks:",
                "      - name: hook_02",
                "        command: test -f {project_root_quoted}/validated_02",
            ]
        )
    )

    states, passes = execute_loop(
        tmp_path,
        manifest_path=manifest,
        round_size=2,
        max_passes=1,
        run_command=(
            "printf '%s\\n' {batch_number} >> {project_root_quoted}/run.log; "
            "touch {project_root_quoted}/validated_{batch_number}"
        ),
        run_validation_hooks_flag=True,
    )

    assert passes == 2
    assert [state.spec.batch_number for state in states] == [1, 2]
    assert all(state.resolved for state in states)
    assert (tmp_path / "run.log").read_text().splitlines() == ["01", "02"]


def test_execute_loop_stops_before_next_batch_when_current_batch_never_validates(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "batch-01.md").write_text("# Batch 01\n\n## Remaining gaps\n")
    (tmp_path / "docs" / "batch-02.md").write_text("# Batch 02\n\n## Remaining gaps\n")
    manifest.write_text(
        "\n".join(
            [
                f"source_root: {tmp_path}",
                "batches:",
                "  - id: batch_01",
                "    number: 1",
                "    focus: first",
                "    status: completed",
                "    record: docs/batch-01.md",
                "    validation_hooks:",
                "      - name: hook_01",
                "        command: test -f {project_root_quoted}/validated_01",
                "  - id: batch_02",
                "    number: 2",
                "    focus: second",
                "    status: completed",
                "    record: docs/batch-02.md",
                "    validation_hooks:",
                "      - name: hook_02",
                "        command: test -f {project_root_quoted}/validated_02",
            ]
        )
    )

    states, passes = execute_loop(
        tmp_path,
        manifest_path=manifest,
        round_size=2,
        max_passes=2,
        run_command="printf '%s\\n' {batch_number} >> {project_root_quoted}/run.log",
        run_validation_hooks_flag=True,
    )

    assert passes == 2
    assert len(states) == 2
    assert states[0].resolved is False
    assert "Validation hook failed: hook_01" in states[0].unresolved_issues
    assert states[1].resolved is False
    assert states[1].validation_ran is False
    assert states[1].unresolved_issues == ["Blocked by unresolved prior batch: batch_01"]
    assert (tmp_path / "run.log").read_text().splitlines() == ["01", "01"]


def test_execute_loop_requires_validation_when_run_command_is_provided(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "batch-01.md").write_text("# Batch 01\n\n## Remaining gaps\n")
    manifest.write_text(
        "\n".join(
            [
                f"source_root: {tmp_path}",
                "batches:",
                "  - id: batch_01",
                "    number: 1",
                "    focus: first",
                "    status: completed",
                "    record: docs/batch-01.md",
            ]
        )
    )

    with pytest.raises(ValueError, match="requires validation hooks or validate commands"):
        execute_loop(
            tmp_path,
            manifest_path=manifest,
            round_size=1,
            max_passes=1,
            run_command="touch {project_root_quoted}/ran",
        )


def test_execute_loop_writes_session_logs_for_attempts(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    session_log_dir = tmp_path / "logs" / "session-01"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "batch-01.md").write_text("# Batch 01\n\n## Remaining gaps\n")
    manifest.write_text(
        "\n".join(
            [
                f"source_root: {tmp_path}",
                "batches:",
                "  - id: batch_01",
                "    number: 1",
                "    focus: first",
                "    status: completed",
                "    record: docs/batch-01.md",
                "    validation_hooks:",
                "      - name: hook_01",
                "        command: test -f {project_root_quoted}/validated_01",
            ]
        )
    )

    states, passes = execute_loop(
        tmp_path,
        manifest_path=manifest,
        round_size=1,
        max_passes=1,
        run_command="touch {project_root_quoted}/validated_{batch_number}",
        run_validation_hooks_flag=True,
        session_log_dir=session_log_dir,
    )

    assert passes == 1
    assert len(states) == 1
    assert states[0].resolved is True

    session_payload = json.loads((session_log_dir / "session.json").read_text())
    attempt_payload = json.loads(
        (session_log_dir / "batches" / "batch_01" / "attempt_01.json").read_text()
    )
    event_types = [
        json.loads(line)["type"]
        for line in (session_log_dir / "events.jsonl").read_text().splitlines()
    ]

    assert session_payload["passes_executed"] == 1
    assert session_payload["resolved_batches"] == ["batch_01"]
    assert "completed_at" in session_payload
    assert attempt_payload["run_result"]["exit_code"] == 0
    assert attempt_payload["post_state"]["resolved"] is True
    assert event_types == [
        "batch_start",
        "batch_attempt",
        "batch_complete",
        "session_complete",
    ]
