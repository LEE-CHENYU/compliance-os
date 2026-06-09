"""Tests for the save_artifact MCP tool."""

import base64
import json

from compliance_os.mcp_server import save_artifact


def test_save_artifact_writes_base64_and_creates_parent_dirs(tmp_path):
    payload = b"%PDF-1.4 fake pdf bytes"
    b64 = base64.b64encode(payload).decode("ascii")
    dest = tmp_path / "newdir" / "form-8843.pdf"  # parent does not exist yet

    result = json.loads(save_artifact(b64, str(dest)))

    assert result["status"] == "success"
    assert result["bytes_written"] == len(payload)
    assert dest.read_bytes() == payload
    assert result["path"] == str(dest.resolve())


def test_save_artifact_writes_text_when_is_text(tmp_path):
    dest = tmp_path / "83b-election-letter.txt"

    result = json.loads(save_artifact("Dear IRS, 83(b) election.", str(dest), is_text=True))

    assert result["status"] == "success"
    assert dest.read_text() == "Dear IRS, 83(b) election."


def test_save_artifact_rejects_invalid_base64_and_writes_nothing(tmp_path):
    dest = tmp_path / "x.pdf"

    result = json.loads(save_artifact("not!!valid!!base64", str(dest)))

    assert result["status"] == "error"
    assert not dest.exists()


def test_save_artifact_rejects_empty_path():
    result = json.loads(save_artifact("aGk=", "   "))
    assert result["status"] == "error"
