# tests/test_cross_check.py
import pytest


def test_load_chains_has_v1_chains():
    from compliance_os.compliance.cross_check import load_chains

    chains = load_chains()
    assert set(chains) == {"stem_opt", "h1b", "tax", "corporate"}
    stem = chains["stem_opt"]
    assert "i20" in stem["detect_when_any"]
    assert "sevis_id" in stem["must_agree"]
    assert any(d["doc_type"] == "i983" and d["required"] for d in stem["documents"])
