"""Tests for the save_artifact MCP tool — including path-containment hardening.

save_artifact is exposed to the model (steerable by untrusted document
content), so it must write ONLY inside the Guardian artifacts root and reject
absolute paths / traversal / sensitive targets that escape it.
"""

import base64
import json

import pytest

from compliance_os.mcp_server import save_artifact


@pytest.fixture(autouse=True)
def _artifacts_root(tmp_path, monkeypatch):
    """Point the artifacts root at an isolated temp dir for every test."""
    root = tmp_path / "artifacts"
    monkeypatch.setenv("GUARDIAN_ARTIFACTS_DIR", str(root))
    return root


# ---- writes inside the root succeed ----

def test_writes_base64_under_root_with_relative_name(_artifacts_root):
    payload = b"%PDF-1.4 fake pdf bytes"
    b64 = base64.b64encode(payload).decode("ascii")

    result = json.loads(save_artifact(b64, "form-8843.pdf"))

    assert result["status"] == "success"
    assert result["bytes_written"] == len(payload)
    dest = _artifacts_root / "form-8843.pdf"
    assert dest.read_bytes() == payload
    assert result["path"] == str(dest.resolve())


def test_relative_subpath_creates_dirs_within_root(_artifacts_root):
    b64 = base64.b64encode(b"x").decode("ascii")
    result = json.loads(save_artifact(b64, "2026/8843.pdf"))
    assert result["status"] == "success"
    assert (_artifacts_root / "2026" / "8843.pdf").exists()


def test_text_mode(_artifacts_root):
    result = json.loads(save_artifact("Dear IRS, 83(b) election.", "letter.txt", is_text=True))
    assert result["status"] == "success"
    assert (_artifacts_root / "letter.txt").read_text() == "Dear IRS, 83(b) election."


def test_absolute_path_inside_root_is_allowed(_artifacts_root):
    b64 = base64.b64encode(b"ok").decode("ascii")
    dest = _artifacts_root / "sub" / "ok.pdf"
    result = json.loads(save_artifact(b64, str(dest)))
    assert result["status"] == "success"
    assert dest.read_bytes() == b"ok"


# ---- containment: writes that escape the root are refused ----

def test_absolute_path_outside_root_is_refused(tmp_path):
    b64 = base64.b64encode(b"evil").decode("ascii")
    outside = tmp_path / "elsewhere" / "evil.pdf"  # sibling of the artifacts root
    result = json.loads(save_artifact(b64, str(outside)))
    assert result["status"] == "error"
    assert "only writes inside" in result["error"]
    assert not outside.exists()


def test_path_traversal_is_refused(_artifacts_root):
    b64 = base64.b64encode(b"evil").decode("ascii")
    result = json.loads(save_artifact(b64, "../../escape.pdf"))
    assert result["status"] == "error"
    assert not (_artifacts_root.parent.parent / "escape.pdf").exists()


def test_home_relative_path_outside_root_is_refused():
    # ~ expands to the real home, which is outside the (temp) artifacts root.
    b64 = base64.b64encode(b"evil").decode("ascii")
    result = json.loads(save_artifact(b64, "~/.ssh/authorized_keys"))
    assert result["status"] == "error"


def test_sensitive_name_within_root_is_refused(_artifacts_root):
    # Even inside the root, obviously sensitive targets are blocked (defense in depth).
    b64 = base64.b64encode(b"evil").decode("ascii")
    result = json.loads(save_artifact(b64, ".ssh/authorized_keys"))
    assert result["status"] == "error"
    assert "sensitive" in result["error"].lower()


# ---- overwrite protection ----

def test_refuses_overwrite_without_flag_then_allows_with_flag(_artifacts_root):
    a = base64.b64encode(b"first").decode("ascii")
    b = base64.b64encode(b"second").decode("ascii")
    assert json.loads(save_artifact(a, "f.pdf"))["status"] == "success"

    blocked = json.loads(save_artifact(b, "f.pdf"))
    assert blocked["status"] == "error"
    assert (_artifacts_root / "f.pdf").read_bytes() == b"first"  # unchanged

    allowed = json.loads(save_artifact(b, "f.pdf", overwrite=True))
    assert allowed["status"] == "success"
    assert (_artifacts_root / "f.pdf").read_bytes() == b"second"


# ---- input validation (unchanged) ----

def test_rejects_invalid_base64_and_writes_nothing(_artifacts_root):
    result = json.loads(save_artifact("not!!valid!!base64", "x.pdf"))
    assert result["status"] == "error"
    assert not (_artifacts_root / "x.pdf").exists()


def test_rejects_empty_path():
    assert json.loads(save_artifact("aGk=", "   "))["status"] == "error"
