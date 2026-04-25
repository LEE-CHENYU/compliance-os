"""Per-search "tuned" persona generator.

The canonical personas (e.g. eb5_specialist, securities_sophisticated)
cover the load-bearing axes of any given vertical, but they're static
by design — every user gets the same three. This module dispatches a
small Claude Haiku call that reads the user's case brief and the
existing personas for the vertical, then drafts a *fourth* persona
focused on whatever the canonical set is most likely to miss for
this specific case.

Design constraints:
- Single Haiku call per search; ~2-5 seconds; ~$0.005.
- Output must be schema-compatible with `Persona` so `build_prompt`
  treats it identically to the canonical personas.
- Failure-tolerant: if the call errors or returns malformed YAML, we
  silently skip the tuned persona and fall back to the canonical
  three. No user-facing error.
"""
from __future__ import annotations

import datetime as _dt
import logging
import re
from pathlib import Path

import anthropic
import httpx
import yaml

from compliance_os.professional_search.personas import Persona, list_personas
from compliance_os.settings import settings

logger = logging.getLogger(__name__)

TUNER_MODEL = "claude-haiku-4-5"
TUNER_TIMEOUT_S = 60

_YAML_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)


def _system_prompt() -> str:
    return (
        "You are a search-strategy designer. Your job is to look at a "
        "case brief and a set of canonical search personas, and design "
        "one ADDITIONAL persona that captures a search axis the "
        "canonical set is most likely to miss for this specific case.\n\n"
        "The tuned persona must be COMPLEMENTARY, not redundant. If the "
        "canonical set already covers a credential-rooted axis (Chambers "
        "rankings, AILA leadership), do not duplicate it. Look for "
        "what is unusually specific about this case — geography, "
        "language, sub-specialty, regulatory wrinkle, deadline pressure, "
        "investor profile, prior-counsel issue — and design the persona "
        "to find firms strong on that specific dimension.\n\n"
        "Your output is a YAML persona file in the same shape as the "
        "canonical ones. Be honest about what counts as a credible "
        "signal: third-party verifiable evidence only. Self-published "
        "marketing does not count."
    )


def _user_prompt(
    case_brief: str,
    vertical: str,
    canonical_personas: list[Persona],
) -> str:
    canonical_summary = "\n\n".join(
        f"### {p.id}\n"
        f"Title: {p.raw.get('title', '')}\n"
        f"Search angle: {(p.raw.get('search_angle') or '').strip()[:400]}"
        for p in canonical_personas
    )
    return (
        f"# Case brief\n\n{case_brief.strip()}\n\n"
        f"# Vertical\n\n{vertical}\n\n"
        f"# Canonical personas already searching\n\n{canonical_summary}\n\n"
        f"# Your task\n\n"
        f"Design ONE additional persona that hunts for a search axis the "
        f"canonical set is likely to miss for THIS specific case. "
        f"Pick the angle that, if the user only had time to add one "
        f"more search, would most increase the diversity / quality of "
        f"firms surfaced.\n\n"
        f"Output ONLY a YAML document inside a ```yaml code fence, "
        f"matching this schema:\n\n"
        f"```yaml\n"
        f"id: <snake_case_id>          # something like: "
        f"`bilingual_intake`, `deadline_pressure`, `prior_counsel_recovery`\n"
        f"vertical: {vertical}\n"
        f"title: \"Human-readable title for this search axis\"\n"
        f"search_angle: |\n"
        f"  2-4 sentences. Specifically what about THIS case makes this "
        f"  axis worth its own search. Be concrete — name the regulatory\n"
        f"  cite, jurisdiction, language, or fact pattern that drives it.\n"
        f"must_weight:\n"
        f"  - \"Verifiable signal A\"\n"
        f"  - \"Verifiable signal B\"\n"
        f"  - \"Verifiable signal C\"\n"
        f"also_value:\n"
        f"  - \"Secondary signal\"\n"
        f"deprioritize:\n"
        f"  - \"What this persona should NOT find\"\n"
        f"target_count: 4\n"
        f"```\n\n"
        f"Hard rules:\n"
        f"- The persona must NOT duplicate any canonical persona's angle.\n"
        f"- Must_weight signals must be third-party verifiable.\n"
        f"- target_count: 3 to 5 — small, focused.\n"
        f"- No prose outside the code fence."
    )


def _extract_yaml(text: str) -> dict:
    m = _YAML_FENCE_RE.search(text)
    body = m.group(1) if m else text
    doc = yaml.safe_load(body)
    if not isinstance(doc, dict):
        raise ValueError("expected YAML mapping")
    for required in ("id", "title", "search_angle"):
        if not doc.get(required):
            raise ValueError(f"missing field: {required}")
    return doc


async def generate_tuned_persona(
    case_brief: str,
    vertical: str,
    output_dir: Path,
) -> Persona | None:
    """Generate one extra persona tuned to this case. Returns None on failure.

    Saves the persona YAML to `<output_dir>/_tuned.yaml` for audit /
    reuse. The runner loads it like any other persona.
    """
    try:
        canonical = list_personas(vertical)
    except FileNotFoundError:
        logger.warning("tuned persona: no canonical personas for vertical %s", vertical)
        return None

    if not settings.anthropic_api_key:
        return None

    http_client = httpx.AsyncClient(timeout=httpx.Timeout(TUNER_TIMEOUT_S, connect=15.0))
    client = anthropic.AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        http_client=http_client,
        max_retries=1,
    )

    try:
        response = await client.messages.create(
            model=TUNER_MODEL,
            max_tokens=2000,
            system=_system_prompt(),
            messages=[{"role": "user", "content": _user_prompt(case_brief, vertical, canonical)}],
        )
        text = "\n".join(b.text for b in response.content if b.type == "text")
        doc = _extract_yaml(text)

        # Force vertical match + tag the id with a `tuned_` prefix so it's
        # always distinguishable from canonical personas in logs/UI.
        doc["vertical"] = vertical
        if not str(doc["id"]).startswith("tuned_"):
            doc["id"] = f"tuned_{doc['id']}"

        # Persist for audit (so the user can see why a particular firm
        # set was surfaced) and so build_prompt can find it on disk.
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "_tuned_persona.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False))
        logger.info(
            "tuned persona generated: id=%s tokens=%d/%d (in/out)",
            doc["id"], response.usage.input_tokens, response.usage.output_tokens,
        )

        return Persona(
            id=doc["id"],
            vertical=vertical,
            title=doc.get("title", doc["id"]),
            path=path,
            raw=doc,
        )
    except Exception as exc:
        logger.warning("tuned persona generation failed; skipping: %s", exc)
        return None
    finally:
        await http_client.aclose()
