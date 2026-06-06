import importlib


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    import compliance_os.consent as consent
    importlib.reload(consent)  # reset module-level session set + re-resolve home
    return consent


def test_no_consent_initially(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    assert consent.has_consent("lawyer-matching") is False


def test_once_does_not_persist(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "once", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("lawyer-matching") is False


def test_session_in_memory_only(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "session", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("lawyer-matching") is True
    assert not (tmp_path / "consent.json").exists()


def test_always_persists_and_survives_reload(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    consent2 = _fresh(monkeypatch, tmp_path)  # simulate process restart
    assert consent2.has_consent("lawyer-matching") is True


def test_revoke_clears_always(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    consent.revoke_consent("lawyer-matching")
    assert consent.has_consent("lawyer-matching") is False


def test_per_purpose_isolation(monkeypatch, tmp_path):
    consent = _fresh(monkeypatch, tmp_path)
    consent.record_consent("lawyer-matching", "always", destination="guardian_cloud", data_categories=["sot_facts"])
    assert consent.has_consent("cpa-matching") is False
