"""End-to-end stdio MCP test for h1b_active_search.

Spawns the Guardian MCP server over stdio (same transport Claude Code
and Codex use) and invokes the tool with the real Klasko package path.
"""

from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, ".")

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

KLASKO = "/Users/lichenyu/accounting/outgoing/klasko/upload_041626"


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "compliance_os.mcp_server"],
    )
    print("Spawning Guardian MCP server over stdio...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Connected: {len(tool_names)} tools")

            if "h1b_active_search" not in tool_names:
                print("FAIL: h1b_active_search not registered")
                return 1

            print("\n1. h1b_active_search — text mode (Klasko package):")
            r = await session.call_tool("h1b_active_search", {"folder": KLASKO})
            text = r.content[0].text
            lines = text.strip().split("\n")
            for l in lines[:14]:
                print(f"   {l}")
            ok_text = (
                "H-1B Petition Package" in text
                and "Coverage by section" in text
                and "Overall:" in text
            )
            print(f"   -> {'PASS' if ok_text else 'FAIL'}")

            print("\n2. h1b_active_search — JSON mode:")
            r = await session.call_tool(
                "h1b_active_search", {"folder": KLASKO, "as_json": True}
            )
            data = json.loads(r.content[0].text)
            ok_json = (
                data.get("template_id") == "h1b_petition"
                and data.get("files_scanned", 0) >= 40
                and "coverage" in data
                and len(data.get("matched", {})) >= 30
            )
            print(f"   template_id: {data.get('template_id')}")
            print(f"   files_scanned: {data.get('files_scanned')}")
            print(f"   matched slots: {len(data.get('matched', {}))}")
            print(f"   missing_required: {len(data.get('missing_required', []))}")
            print(f"   coverage A/B/C/D/E/F/G:",
                  {k: round(v, 2) for k, v in data.get("coverage", {}).items()})
            print(f"   -> {'PASS' if ok_json else 'FAIL'}")

            print("\n3. h1b_active_search — missing folder:")
            r = await session.call_tool(
                "h1b_active_search", {"folder": "/nope/does/not/exist"}
            )
            err = json.loads(r.content[0].text)
            ok_err = "error" in err
            print(f"   response: {err}")
            print(f"   -> {'PASS' if ok_err else 'FAIL'}")

            all_ok = ok_text and ok_json and ok_err
            print("\n" + "="*50)
            print(f"  STDIO E2E: {'3/3 PASS' if all_ok else 'FAIL'}")
            print("="*50)
            return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
