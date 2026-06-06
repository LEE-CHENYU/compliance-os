import json


def test_lawyer_search_plan_includes_transparency_note(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    from compliance_os import mcp_server

    # lawyer_search_plan requires case_brief + purpose; vertical defaults to
    # "immigration_attorney" (the only persona directory shipped).
    out = mcp_server.lawyer_search_plan(
        case_brief="F-1 student seeking an immigration attorney for an H-1B cap petition.",
        purpose="H-1B petition - 2026 cap",
    )
    data = json.loads(out)
    assert "privacy_note" in data
    assert "generic" in data["privacy_note"].lower()
    assert "personal facts are not included" in data["privacy_note"].lower()
