"""End-to-end test for the hosted MCP endpoint over SSE wire."""

import asyncio
import json
import sys

sys.path.insert(0, ".")

from mcp.client.sse import sse_client
from mcp import ClientSession
from compliance_os.web.services.auth_service import create_token

TOKEN = create_token("af9f31cc-b446-47f0-9604-e81bbc53b67e", "fretin13@gmail.com")
URL = "http://127.0.0.1:8001/mcp/sse"


async def main():
    print(f"Connecting to hosted MCP at {URL}")
    headers = {"Authorization": f"Bearer {TOKEN}"}

    async with sse_client(URL, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Connected: {len(tools.tools)} tools\n")

            results = {}

            # 1. guardian_status (auth → loopback API → DB)
            print("1. guardian_status (auth + API + DB):")
            r = await session.call_tool("guardian_status", {})
            t = r.content[0].text
            ok = "Compliance Status" in t
            for line in t.strip().split("\n")[:6]:
                print(f"   {line}")
            results["guardian_status"] = ok
            print(f"   -> {'PASS' if ok else 'FAIL'}\n")

            # 2. guardian_deadlines
            print("2. guardian_deadlines:")
            r = await session.call_tool("guardian_deadlines", {})
            t = r.content[0].text
            ok = "Deadline" in t or "deadline" in t
            print(f"   {t[:120]}")
            results["guardian_deadlines"] = ok
            print(f"   -> {'PASS' if ok else 'FAIL'}\n")

            # 3. generate_form_8843 (local)
            print("3. generate_form_8843 (local, no auth):")
            r = await session.call_tool("generate_form_8843", {
                "full_name": "Hosted Test User",
                "country_citizenship": "China",
                "visa_type": "F-1",
                "arrival_date": "2022-08-15",
                "days_present_current": 183,
                "school_name": "MIT",
            })
            d = json.loads(r.content[0].text)
            ok = d.get("status") == "success"
            print(f"   status={d.get('status')}, pdf_size={d.get('pdf_size_bytes', 0)}B")
            results["generate_form_8843"] = ok
            print(f"   -> {'PASS' if ok else 'FAIL'}\n")

            # 4. run_compliance_check (local)
            print("4. run_compliance_check/fbar (local):")
            r = await session.call_tool("run_compliance_check", {
                "check_type": "fbar",
                "inputs_json": json.dumps({
                    "accounts": [{"institution_name": "ICBC", "country": "China", "max_balance_usd": 15000}],
                }),
            })
            d4 = json.loads(r.content[0].text)
            ok = d4.get("requires_fbar") is True
            print(f"   requires_fbar={d4.get('requires_fbar')}, agg=${d4.get('aggregate_max_balance_usd', 0):,.0f}")
            results["fbar_check"] = ok
            print(f"   -> {'PASS' if ok else 'FAIL'}\n")

            # 5. guardian_documents (auth)
            print("5. guardian_documents (auth):")
            r = await session.call_tool("guardian_documents", {})
            t = r.content[0].text
            ok = "Documents" in t or "No documents" in t
            print(f"   {t[:120]}")
            results["guardian_documents"] = ok
            print(f"   -> {'PASS' if ok else 'FAIL'}\n")

            # 6. guardian_ask (auth + LLM)
            print("6. guardian_ask (auth + LLM):")
            try:
                r = await asyncio.wait_for(
                    session.call_tool("guardian_ask", {"question": "Do I need to file FBAR?"}),
                    timeout=45,
                )
                t = r.content[0].text
                ok = len(t) > 50 and "Error" not in t
                print(f"   {t[:200]}")
                results["guardian_ask"] = ok
                print(f"   -> {'PASS' if ok else 'FAIL'}\n")
            except asyncio.TimeoutError:
                results["guardian_ask"] = False
                print("   TIMEOUT (45s)")
                print("   -> SKIP\n")

            passed = sum(results.values())
            total = len(results)
            print("=" * 50)
            for name, ok in results.items():
                print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            print(f"\n  HOSTED E2E: {passed}/{total} passed")
            print("=" * 50)


asyncio.run(main())
