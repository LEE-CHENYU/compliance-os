import asyncio


def test_guardian_ask_local_makes_no_external_llm_call(monkeypatch, tmp_path):
    monkeypatch.setenv("GUARDIAN_MODE", "local")
    monkeypatch.setenv("GUARDIAN_HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from compliance_os.web.models import database
    database._engine = None
    database._SessionLocal = None
    from compliance_os import mcp_server

    # Any hosted egress path must NOT be reached in local mode.
    async def _boom(*a, **k):
        raise AssertionError("guardian_ask hit the hosted /api/chat path in local mode")
    monkeypatch.setattr(mcp_server, "_api_post", _boom)

    out = asyncio.run(mcp_server.guardian_ask("Do I need to file FBAR?"))
    assert isinstance(out, str) and out  # returns local grounding, no external call
    database._engine = None
    database._SessionLocal = None
