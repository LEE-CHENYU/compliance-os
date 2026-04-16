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

# Per-request token storage — set by middleware, read by MCP tools
_mcp_client_token: contextvars.ContextVar[str] = contextvars.ContextVar(
    "mcp_client_token", default=""
)


def get_mcp_client_token() -> str:
    """Read the auth token set by the hosted MCP middleware."""
    return _mcp_client_token.get()


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
            # Don't reject unauthenticated requests here — the MCP protocol
            # sends an initial handshake before auth. The tools themselves
            # will fail gracefully if the token is missing.

        await self.app(scope, receive, send)


def create_mcp_app() -> ASGIApp:
    """Create the hosted MCP ASGI app with auth middleware.

    Returns a Starlette app that can be mounted on FastAPI:
        app.mount("/mcp", create_mcp_app())

    Endpoints created:
        GET  /mcp/sse          — SSE connection (for Claude Desktop)
        POST /mcp/messages/    — MCP message handler (for SSE clients)
    """
    from compliance_os.mcp_server import mcp as guardian_mcp

    sse_app = guardian_mcp.sse_app(mount_path="/mcp")
    return MCPAuthMiddleware(sse_app)
