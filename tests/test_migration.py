"""Tests for migration.py, mcp_install local-mode, and version bump."""
import io
import json
import os
import zipfile
from pathlib import Path

import pytest


def test_mcp_server_config_is_local_mode():
    from compliance_os.mcp_install import _mcp_server_config

    cfg = _mcp_server_config("gdn_oc_aa_bb")
    assert cfg["env"] == {"GUARDIAN_LICENSE_KEY": "gdn_oc_aa_bb", "GUARDIAN_MODE": "local"}
    assert cfg["args"] == ["-m", "compliance_os.mcp_server"]


def test_write_toml_config_writes_local_env(tmp_path):
    from compliance_os.mcp_install import _write_toml_config

    path = tmp_path / "config.toml"
    _write_toml_config(path, "gdn_oc_cc_dd")
    text = path.read_text()
    assert 'GUARDIAN_LICENSE_KEY = "gdn_oc_cc_dd"' in text
    assert 'GUARDIAN_MODE = "local"' in text
    assert "GUARDIAN_API_URL" not in text
