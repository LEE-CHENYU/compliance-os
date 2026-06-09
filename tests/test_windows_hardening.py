"""Windows-compatibility hardening regression tests (2.0.4).

The Guardian local extension installs into a read-only DXT/uv cache, so all
per-user writable state must resolve under GUARDIAN_HOME (~/.guardian), and all
JSON I/O must be utf-8 (Windows `open()` defaults to cp1252, which can corrupt a
hand-edited or non-ASCII license.json / consent.json).
"""
from __future__ import annotations

import importlib
import json


def test_consent_store_is_utf8(monkeypatch, tmp_path):
    """A non-ASCII purpose round-trips — proves the consent store writes/reads
    utf-8 rather than the platform default."""
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    import compliance_os.consent as consent

    importlib.reload(consent)
    consent.record_consent("café-naïve-Ä", "always", destination="guardian_cloud",
                           data_categories=["sot_facts"])
    assert consent.has_consent("café-naïve-Ä")
    # The store round-trips a non-ASCII purpose, and the file decodes as utf-8
    # with the purpose preserved (json escapes it, so parse rather than substring).
    store = json.loads((tmp_path / "consent.json").read_bytes().decode("utf-8"))
    assert "café-naïve-Ä" in store


def test_license_cache_is_utf8(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    import compliance_os.licensing as licensing

    importlib.reload(licensing)
    licensing._write_cache({"valid": True, "note": "café"})
    assert licensing._read_cache().get("valid") is True
    assert json.loads((tmp_path / "license.json").read_bytes().decode("utf-8"))["note"] == "café"


def test_per_user_paths_resolve_under_guardian_home(monkeypatch, tmp_path):
    """diligence DB + professional-search output + chroma must live under
    GUARDIAN_HOME, not the (read-only on Windows) installed package dir."""
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATA_DIR", raising=False)
    import compliance_os.settings as settings_mod

    importlib.reload(settings_mod)
    s = settings_mod.settings
    assert str(s.diligence_db_path).startswith(str(tmp_path)), s.diligence_db_path
    assert str(s.professional_search_output_dir).startswith(str(tmp_path)), s.professional_search_output_dir
