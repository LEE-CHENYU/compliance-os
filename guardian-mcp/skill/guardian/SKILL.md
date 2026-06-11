---
name: guardian
description: Start the Guardian compliance copilot — F-1/J-1/H-1B status, nonresident tax (Form 8843, 1040-NR), foreign-owned US entities (Form 5472), 83(b) elections, and FBAR. Use when the user types /guardian (optionally followed by their situation) or explicitly asks to start, launch, or open Guardian.
---

# Start Guardian

1. Immediately call the `start_guardian` tool from the Guardian Compliance connector — before any other tool. Pass everything the user typed after `/guardian` as `situation` (empty if they typed nothing).
2. The tool returns Guardian's cold-start kickoff instructions. Follow them exactly, and always show Guardian's output to the user in full — never silently consume a Guardian tool result and move on to something else.
3. If no Guardian tools are available in this conversation, say so plainly: the Guardian Compliance extension isn't enabled here (enable it under Settings → Extensions, or via this chat's tools menu). Do not improvise a compliance answer in its place — Guardian's answers must be grounded in its tools.
