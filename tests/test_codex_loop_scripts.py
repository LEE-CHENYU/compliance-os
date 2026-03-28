from pathlib import Path
import os
import signal
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_codex_loop_shell_scripts_are_syntax_valid():
    scripts = [
        ROOT / "scripts" / "codex_loop" / "common.sh",
        ROOT / "scripts" / "codex_loop" / "control.sh",
        ROOT / "scripts" / "codex_loop" / "codex_data_room_loop.sh",
        ROOT / "scripts" / "codex_loop" / "run_batch_iteration.sh",
    ]

    for script in scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


def test_run_batch_iteration_echo_provider_renders_prompt():
    script = ROOT / "scripts" / "codex_loop" / "run_batch_iteration.sh"
    result = subprocess.run(
        [
            "bash",
            str(script),
            "01",
            "batch_01",
            "STEM OPT and entity core records",
            "docs/data-room-batch-01.md",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "ROOT": str(ROOT),
            "PROVIDER": "echo",
            "PYTHON_BIN": "python3",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "CURRENT BATCH:" in result.stdout
    assert "batch_number: 01" in result.stdout
    assert "MANDATORY WORKFLOW:" in result.stdout
    assert "scripts/data_room_batch_loop.py" in result.stdout


def test_control_script_start_status_stop_cycle(tmp_path):
    control_script = ROOT / "scripts" / "codex_loop" / "control.sh"
    temp_root = tmp_path / "root"
    loop_dir = temp_root / "scripts" / "codex_loop"
    config_dir = temp_root / "config"
    log_dir = temp_root / "logs" / "codex_loop"
    loop_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)

    loop_script = loop_dir / "codex_data_room_loop.sh"
    loop_script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "ROOT=\"${ROOT:?}\"\n"
        "LOG_DIR=\"$ROOT/logs/codex_loop\"\n"
        "STOPFILE=\"$LOG_DIR/codex_data_room_loop.stop\"\n"
        "mkdir -p \"$LOG_DIR\"\n"
        "printf 'stub-loop-start\\n'\n"
        "while true; do\n"
        "  if [ -f \"$STOPFILE\" ]; then\n"
        "    printf 'stub-loop-stop\\n'\n"
        "    rm -f \"$STOPFILE\"\n"
        "    exit 0\n"
        "  fi\n"
        "  sleep 1\n"
        "done\n"
    )
    loop_script.chmod(0o755)

    (config_dir / "codex_loop.yaml").write_text(
        "provider: echo\n"
        "model: gpt-5.4-codex\n"
        "reasoning_effort: xhigh\n"
    )

    env = {
        **os.environ,
        "ROOT": str(temp_root),
        "CODEX_LOOP_CONFIG": str(config_dir / "codex_loop.yaml"),
    }

    start = subprocess.run(
        ["bash", str(control_script), "start"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert start.returncode == 0, start.stderr
    assert "Started with PID:" in start.stdout

    status = subprocess.run(
        ["bash", str(control_script), "status"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert status.returncode == 0, status.stderr
    assert "Running (PID:" in status.stdout

    pidfile = log_dir / "codex_data_room_loop.pid"
    assert pidfile.exists()
    pid = int(pidfile.read_text().strip())
    os.kill(pid, 0)

    stop = subprocess.run(
        ["bash", str(control_script), "stop"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert stop.returncode == 0, stop.stderr

    deadline = time.time() + 10
    while time.time() < deadline:
        status = subprocess.run(
            ["bash", str(control_script), "status"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if "Not running" in status.stdout:
            break
        time.sleep(0.5)
    else:
        os.kill(pid, signal.SIGTERM)
        pytest.fail("loop did not stop within deadline")

    assert not pidfile.exists()
