"""The startup update notice: a side-loaded DXT pins an exact version and never
auto-updates, so entry-point tools nudge the user when a newer version exists."""

from compliance_os import mcp_server as M


def test_ver_tuple_parses_and_orders():
    assert M._ver_tuple("2.0.10") == (2, 0, 10)
    assert M._ver_tuple("2.0.9") > M._ver_tuple("2.0.8")
    assert M._ver_tuple("garbage") == (0, 0, 0)


def test_update_notice_empty_when_current(monkeypatch):
    monkeypatch.setattr(M, "_UPDATE_LATEST", None)
    assert M._update_notice() == ""


def test_update_notice_present_when_behind(monkeypatch):
    monkeypatch.setattr(M, "_UPDATE_LATEST", "2.9.9")
    notice = M._update_notice()
    assert "2.9.9" in notice
    assert "reinstall" in notice.lower()


def test_start_guardian_prepends_notice_when_behind(monkeypatch):
    monkeypatch.setattr(M, "_UPDATE_LATEST", "2.9.9")
    out = M.start_guardian("F-1 internship")
    assert out.startswith("ℹ️ Guardian 2.9.9")
    # the kickoff still follows the notice
    assert out.endswith(M._guardian_kickoff("F-1 internship"))


def test_start_guardian_no_notice_when_current(monkeypatch):
    monkeypatch.setattr(M, "_UPDATE_LATEST", None)
    assert M.start_guardian("") == M._guardian_kickoff("")
