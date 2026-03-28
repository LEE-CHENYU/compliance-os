from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_codex_loop_shell_scripts_are_syntax_valid():
    scripts = [
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
