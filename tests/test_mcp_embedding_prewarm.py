import os

import pytest

os.environ.setdefault("GUARDIAN_DISABLE_PREWARM", "1")

from compliance_os import mcp_server
from compliance_os.query import engine as query_engine


@pytest.fixture(autouse=True)
def reset_embedding_prewarm_state():
    mcp_server._EMBED_READY.set()
    mcp_server._EMBED_ERROR = None
    yield
    mcp_server._EMBED_READY.set()
    mcp_server._EMBED_ERROR = None


def test_ensure_embeddings_ready_retries_after_failed_prewarm(monkeypatch):
    calls = []

    def resolve_embed_model():
        calls.append("retry")
        return object()

    monkeypatch.setattr(query_engine, "resolve_embed_model", resolve_embed_model)
    mcp_server._EMBED_ERROR = RuntimeError("first failure")

    assert mcp_server._ensure_embeddings_ready(wait_timeout=0.01) is None
    assert calls == ["retry"]
    assert mcp_server._EMBED_ERROR is None


def test_ensure_embeddings_ready_reports_unavailable_after_retry_failure(monkeypatch):
    def resolve_embed_model():
        raise RuntimeError("second failure")

    monkeypatch.setattr(query_engine, "resolve_embed_model", resolve_embed_model)
    mcp_server._EMBED_ERROR = RuntimeError("first failure")

    result = mcp_server._ensure_embeddings_ready(wait_timeout=0.01)

    assert result is not None
    error_code, message = result
    assert error_code == "embeddings_unavailable"
    assert "second failure" in message
    assert isinstance(mcp_server._EMBED_ERROR, RuntimeError)
