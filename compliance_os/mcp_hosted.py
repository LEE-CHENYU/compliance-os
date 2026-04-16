"""Hosted MCP endpoint — mounts on the existing FastAPI server.

Exposes the Guardian MCP tools over HTTP so GUI users (Claude Desktop,
Codex app) can connect with just a URL and token. No Python install needed.

Architecture:
  - Client connects to /mcp with Authorization: Bearer <token>
  - Auth middleware validates the token and stores it per-request
  - MCP tools call the local API with this token (loopback)
  - Works with both SSE and Streamable HTTP transports
"""

from __future__ import annotations

import contextvars
import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Per-request storage — set by middleware, read by MCP tools
_mcp_client_token: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_client_token", default=""
)
_mcp_api_base: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_api_base", default=""
)


def get_mcp_client_token() -> str:
    """Read the auth token set by the hosted MCP middleware."""
    return _mcp_client_token.get()


def get_mcp_api_base() -> str:
    """Read the loopback API URL derived from the incoming request."""
    return _mcp_api_base.get()


class MCPAuthMiddleware:
    """ASGI middleware that extracts Bearer token from MCP HTTP requests.

    Sets a contextvar so MCP tool handlers can use the client's auth
    token for Guardian API calls.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_value = headers.get(b"authorization", b"").decode()
            token = auth_value.removeprefix("Bearer ").strip()

            if token:
                _mcp_client_token.set(token)

            # Derive the loopback API URL so MCP tools can call
            # the same server they're hosted on (not a hardcoded port).
            host = headers.get(b"host", b"localhost").decode()
            scheme = "https" if scope.get("scheme") == "https" else "http"
            _mcp_api_base.set(f"{scheme}://{host}")

        await self.app(scope, receive, send)


def create_mcp_app() -> ASGIApp:
    """Create the hosted MCP ASGI app with auth middleware.

    Returns a Starlette app that can be mounted on FastAPI:
        app.mount("/mcp", create_mcp_app())

    Endpoints created:
        GET  /mcp/sse          — SSE connection (for Claude Desktop)
        POST /mcp/messages/    — MCP message handler (for SSE clients)
    """
    import compliance_os.mcp_server as srv

    # When hosted, the MCP tools call the same FastAPI process via loopback.
    # Override the API URL at module level so all tool calls target the
    # correct server — even when running in a thread pool.
    import os

    port = os.environ.get("PORT", os.environ.get("UVICORN_PORT", "8000"))
    hosted_url = os.environ.get(
        "GUARDIAN_HOSTED_API_URL", f"http://127.0.0.1:{port}"
    )
    srv.GUARDIAN_API_URL = hosted_url
    logger.info("Hosted MCP: API loopback URL set to %s", hosted_url)

    # mount_path must NOT include the FastAPI mount prefix — FastAPI's
    # app.mount("/mcp", ...) already handles the /mcp prefix.
    sse_app = srv.mcp.sse_app()
    return MCPAuthMiddleware(sse_app)
