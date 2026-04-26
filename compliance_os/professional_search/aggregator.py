"""Shared helpers for loading + deduplicating per-persona search results.

Lives in `compliance_os.professional_search` (the package, not the web layer)
so both the FastAPI router and the background runner can import it without
creating a service→router back-edge. The router would otherwise be the
implicit "owner" of these helpers, which is a layering inversion.

Two functions:

- `load_persona_yamls(row)` — read every completed persona's YAML output
  from disk, return `{persona_id: parsed_doc}`.
- `aggregate_firms(persona_yamls)` — dedupe firms across personas, merge
  rationales/credentials/sources/risks. Output is a list of "firm" dicts
  with `_personas`, `_why_fits`, `_credentials`, `_risks`, `_sources`
  fields added — JSON-safe (no tuples) so the result round-trips through
  Postgres JSONB columns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml as _yaml


def load_persona_yamls(row: Any) -> dict[str, dict]:
    """Read every completed persona's YAML output, keyed by persona id.

    `row` must expose a `persona_status` dict whose values look like
    `{"status": "complete", "output_path": "/abs/path.yaml"}`. Missing
    files and parse errors are silently skipped — the caller decides
    what to do with an empty result.
    """
    out: dict[str, dict] = {}
    for persona_id, status in (row.persona_status or {}).items():
        if status.get("status") != "complete":
            continue
        path_str = status.get("output_path")
        if not path_str:
            continue
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            doc = _yaml.safe_load(path.read_text()) or {}
        except Exception:
            continue
        if isinstance(doc, dict):
            out[persona_id] = doc
    return out


def aggregate_firms(persona_yamls: dict[str, dict]) -> list[dict]:
    """Dedupe firms across personas; merge rationales, credentials, sources.

    Returns a list of unified firm records sorted by max confidence
    desc. Each record has the original firm fields plus:
      - `_personas`:  list of persona ids that surfaced this firm
      - `_why_fits`:  list of [persona_id, why_fit] pairs (lists, not
                      tuples — for JSONB-binder compatibility)
      - `_credentials`: deduped credential strings (preserve first-seen order)
      - `_risks`:     deduped risk strings
      - `_sources`:   deduped source URLs
    """
    by_key: dict[str, dict] = {}
    seen_creds: dict[str, set[str]] = {}
    seen_risks: dict[str, set[str]] = {}
    seen_sources: dict[str, set[str]] = {}

    for persona_id, doc in persona_yamls.items():
        for firm in (doc.get("firms") or []):
            name = (firm.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key not in by_key:
                by_key[key] = {
                    **{
                        k: v
                        for k, v in firm.items()
                        if k not in {"credentials", "risks", "sources", "why_fit"}
                    },
                    "_personas": [],
                    "_why_fits": [],
                    "_credentials": [],
                    "_risks": [],
                    "_sources": [],
                }
                seen_creds[key] = set()
                seen_risks[key] = set()
                seen_sources[key] = set()
            entry = by_key[key]
            entry["_personas"].append(persona_id)

            if firm.get("why_fit"):
                # Stored as a 2-element list (not tuple) so the result is
                # JSON-serializable on every backend — psycopg's JSONB
                # binder rejects tuples in some versions.
                entry["_why_fits"].append([persona_id, firm["why_fit"].strip()])

            # Take max confidence across personas.
            cur = entry.get("confidence") or 0
            new = firm.get("confidence") or 0
            if new > cur:
                entry["confidence"] = new

            # Take richest contact info: prefer non-null fields from later
            # personas only if the existing slot is empty.
            for field in (
                "lead_attorney", "role", "phone", "email",
                "website", "city", "state",
                "consultation_fee_low", "consultation_fee_high",
                "petition_fee_low", "petition_fee_high",
                "service_fee_label", "fee_basis",
                "litigation_capability",
            ):
                if entry.get(field) in (None, "") and firm.get(field) not in (None, ""):
                    entry[field] = firm[field]

            for c in firm.get("credentials") or []:
                if c not in seen_creds[key]:
                    seen_creds[key].add(c)
                    entry["_credentials"].append(c)
            for r in firm.get("risks") or []:
                if r not in seen_risks[key]:
                    seen_risks[key].add(r)
                    entry["_risks"].append(r)
            for s in firm.get("sources") or []:
                if s not in seen_sources[key]:
                    seen_sources[key].add(s)
                    entry["_sources"].append(s)

    out = list(by_key.values())
    out.sort(key=lambda f: -(f.get("confidence") or 0))
    return out
