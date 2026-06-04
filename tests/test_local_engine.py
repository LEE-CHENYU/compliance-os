# tests/test_local_engine.py
# Module import header — all tests in this file rely on these.
import asyncio
import os
from pathlib import Path

import pytest


def test_local_mode_db_url_points_at_guardian_home(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # configured_database_url() reads env live, so no module reload is needed.
    from compliance_os.web.models import database

    url = database.configured_database_url()
    assert url == f"sqlite:///{tmp_path / 'guardian.db'}"


def test_hosted_mode_db_url_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "hosted")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from compliance_os.web.models import database

    url = database.configured_database_url()
    assert url.endswith("copilot.db")
