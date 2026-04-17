"""Template-parameterized stdio MCP E2E test.

Spawns the Guardian MCP server over stdio and exercises case_active_search
against each supplied (template, folder) pair. Replaces the H-1B-specific
test script so future templates (CPA, ...) require no new scripts.

Usage:
    python scripts/test_case_template_mcp.py              # default pairs
    python scripts/test_case_template_mcp.py h1b /path    # ad-hoc run
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession


DEFAULT_PAIRS: list[tuple[str, str, float]] = [
    # (template, folder, min required-coverage pct)
    ("h1b", "/Users/lichenyu/accounting/outgoing/klasko/upload_041626", 90.0),
    ("cpa", "/Users/lichenyu/accounting/outgoing/kaufman_rossin/data_room", 90.0),
]


async def run_one(session: ClientSession, template: str, folder: str, min_pct: float) -> bool:
    path = Path(folder)
    if not path.is_dir():
        print(f"  SKIP — {folder} not a directory")
        return True

    # Text mode — sanity check the formatted report
    r = await session.call_tool(
        "case_active_search", {"template": template, "folder": folder}
    )
    text = r.content[0].text
    text_ok = (
        "Active Search Report" in text
        and "Coverage by section" in text
        and "Overall:" in text
    )

    # JSON mode — structured coverage check
    r = await session.call_tool(
        "case_active_search",
        {"template": template, "folder": folder, "as_json": True},
    )
    data = json.loads(r.content[0].text)
    req_total = sum(
        len([sl for sl in data.get("missing_required", [])])
        + sum(1 for s in data.get("matched", {}))
        for _ in [0]
    )
    # Easier: compute from coverage + missing
    coverage = data.get("coverage", {})
    files = data.get("files_scanned", 0)
    missing_req = data.get("missing_required", [])
    matched_ct = len(data.get("matched", {}))

    # Coverage is per-section. Compute overall required coverage from
    # the returned matched/missing lists.
    from compliance_os.case_templates import resolve_template
    tpl = resolve_template(template)
    required_ids = {s.id for s in tpl.slots if s.required}
    matched_required = required_ids & set(data.get("matched", {}).keys())
    req_pct = 100.0 * len(matched_required) / max(1, len(required_ids))

    json_ok = (
        data.get("template_id") == tpl.id
        and files > 0
        and req_pct >= min_pct
    )

    print(f"  template     : {template} ({tpl.name})")
    print(f"  files        : {files}")
    print(f"  matched slots: {matched_ct}")
    print(f"  required     : {len(matched_required)}/{len(required_ids)} ({req_pct:.0f}%)")
    print(f"  missing req  : {[m['id'] for m in missing_req]}")
    print(f"  coverage A-G : {coverage}")
    print(f"  text mode    : {'PASS' if text_ok else 'FAIL'}")
    print(f"  json mode    : {'PASS' if json_ok else 'FAIL'}")
    return text_ok and json_ok


async def run_error_cases(session: ClientSession) -> bool:
    print("\n-- error cases --")
    # Unknown template
    r = await session.call_tool(
        "case_active_search", {"template": "nope", "folder": "/tmp"}
    )
    data = json.loads(r.content[0].text)
    unknown_ok = "error" in data and "Unknown template" in data["error"]
    print(f"  unknown template -> {'PASS' if unknown_ok else 'FAIL'}")

    # Missing folder
    r = await session.call_tool(
        "case_active_search",
        {"template": "h1b", "folder": "/nope/does/not/exist"},
    )
    data = json.loads(r.content[0].text)
    missing_ok = "error" in data
    print(f"  missing folder   -> {'PASS' if missing_ok else 'FAIL'}")
    return unknown_ok and missing_ok


async def main() -> int:
    argv = sys.argv[1:]
    if len(argv) == 2:
        pairs = [(argv[0], argv[1], 80.0)]
    elif len(argv) == 0:
        pairs = DEFAULT_PAIRS
    else:
        print("Usage: test_case_template_mcp.py [<template> <folder>]", file=sys.stderr)
        return 2

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "compliance_os.mcp_server"],
    )
    print("Spawning Guardian MCP server over stdio...")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            print(f"Connected: {len(tool_names)} tools")
            required = {"case_active_search", "h1b_active_search", "cpa_active_search"}
            missing = required - tool_names
            if missing:
                print(f"FAIL: MCP server missing tools {missing}")
                return 1

            all_ok = True
            for template, folder, min_pct in pairs:
                print(f"\n-- {template} : {folder} --")
                ok = await run_one(session, template, folder, min_pct)
                all_ok = all_ok and ok

            ok = await run_error_cases(session)
            all_ok = all_ok and ok

    print("\n" + "=" * 50)
    total = len(pairs) + 1
    print(f"  STDIO E2E: {'ALL PASS' if all_ok else 'FAIL'} ({total} groups)")
    print("=" * 50)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
